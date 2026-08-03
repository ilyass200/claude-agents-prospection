# Connecteur IMAP Hostinger

## Présentation

Ce connecteur permet de lire les emails entrants depuis **les boîtes mail de tous les senders actifs**. Il est utilisé exclusivement par l'**Agent Fetch Replies** pour détecter les réponses des prospects et mettre à jour le tracking Google Sheets. Une connexion IMAP distincte est établie pour chaque sender défini dans `senders.json`.

---

## Configuration

Les credentials IMAP sont stockés uniquement dans `senders.json` — il n'existe pas de variables globales `$IMAP_EMAIL` / `$IMAP_PASSWORD` dans `.env`. Chaque sender y définit sa configuration complète ; seule la valeur du mot de passe (référencée par nom via `imap_password_var`) est lue dans `.env`.

```
imap_host     : sender.imap_host     ← défini dans senders.json
imap_port     : sender.imap_port     ← défini dans senders.json (défaut 993)
imap_email    : sender.imap_email    ← défini dans senders.json
imap_password : sender.imap_password ← résolu depuis la variable nommée dans sender.imap_password_var (.env)
```

> ⚠️ Le code Python doit recevoir ces credentials en paramètres, pas les lire depuis `os.environ`.

---

## Connexion IMAP

Les credentials sont passés en paramètres (résolus depuis `senders.json` par l'Orchestrateur).

```python
import imaplib, email
from email.header import decode_header

def connect_imap(imap_host, imap_port, imap_email, imap_password):
    """Connexion IMAP pour un sender donné. Retourne l'objet imap connecté."""
    imap = imaplib.IMAP4_SSL(imap_host, int(imap_port))
    imap.login(imap_email, imap_password)
    imap.select("INBOX")
    return imap

# Exemple d'appel depuis l'Agent Fetch Replies :
# imap = connect_imap(sender.imap_host, sender.imap_port, sender.imap_email, sender.imap_password)
```

> ⚠️ Toujours appeler `imap.logout()` en fin de session pour chaque sender.

---

## Recherche des emails récents

Cherche les emails reçus depuis les N derniers jours dans la boîte INBOX.

```python
import datetime

def fetch_recent_emails(imap, since_days=30):
    """Retourne la liste des emails reçus depuis since_days jours."""
    since_date = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")
    status, message_ids = imap.search(None, f'(SINCE "{since_date}")')
    if status != "OK":
        return []
    ids = message_ids[0].split()
    emails = []
    for mid in ids:
        status, msg_data = imap.fetch(mid, "(RFC822)")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        emails.append(parse_email(msg))
    return emails

def parse_email(msg):
    """Extrait les champs utiles d'un email brut."""
    # Décode le sujet
    subject_raw, encoding = decode_header(msg["Subject"] or "")[0]
    subject = subject_raw.decode(encoding or "utf-8") if isinstance(subject_raw, bytes) else subject_raw

    # Extrait l'adresse de l'expéditeur
    from_raw = msg.get("From", "")
    sender_email = email.utils.parseaddr(from_raw)[1].lower().strip()

    # Extrait la date
    date_str = msg.get("Date", "")

    # Extrait le corps en texte brut
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                charset = part.get_content_charset() or "utf-8"
                body = part.get_payload(decode=True).decode(charset, errors="replace")
                break
    else:
        if msg.get_content_type() == "text/plain":
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")

    # Nettoie le corps : supprime les citations (lignes commençant par >)
    lines = body.splitlines()
    clean_lines = [l for l in lines if not l.strip().startswith(">") and l.strip() != ""]
    clean_body = "\n".join(clean_lines[:20])  # 20 lignes max

    return {
        "sender_email": sender_email,
        "subject": subject,
        "date": date_str,
        "body": clean_body
    }
```

---

## Filtrage — Identifier les réponses de prospects

Un email est considéré comme une **réponse d'un prospect** si :
1. `sender_email` correspond à un email présent dans la colonne **F** (email) du Google Sheet

> Note : la vérification du sujet (`Re:`) n'est pas implémentée dans le code — le matching par email expéditeur suffit et évite les faux positifs liés aux variations d'objet.

```python
def match_reply_to_lead(parsed_email, leads):
    """
    Cherche si l'email correspond à un lead connu.
    leads = liste de dicts avec au moins 'email', 'objet_email_envoye', 'row_index'
    Retourne le lead matchant ou None.
    """
    sender = parsed_email["sender_email"]
    for lead in leads:
        if lead.get("email", "").lower().strip() == sender:
            return lead
    return None
```

---

## Décision par type de réponse

Après avoir matché un email à un lead, analyser le corps pour qualifier la réponse :

| Signal dans le corps | Statut à écrire | Prochaine action |
|---|---|---|
| "pas intéressé", "non merci", "stop", "unsubscribe", "désinscription" | `Réponse négative` | Archiver — ne plus contacter |
| "intéressé", "disponible", "oui", "appel", "rendez-vous", "quand", "calendly" | `Réponse positive` | Alerter l'Orchestrateur |
| Toute autre réponse | `Réponse neutre` | Alerter l'Orchestrateur |

> En cas de doute → classifier `Réponse neutre` et remonter à l'Orchestrateur.

```python
NEGATIVE_KEYWORDS = ["pas intéressé", "non merci", "stop", "unsubscribe", "désinscription", "ne pas contacter", "remove", "opt out"]
POSITIVE_KEYWORDS = ["intéressé", "disponible", "oui", "appel", "rendez-vous", "quand", "calendly", "discuter", "15 minutes", "call", "me contacter", "contactez-moi", "appelez-moi", "n'hésitez pas à"]

def classify_reply(body):
    body_lower = body.lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw in body_lower:
            return "Réponse négative"
    for kw in POSITIVE_KEYWORDS:
        if kw in body_lower:
            return "Réponse positive"
    return "Réponse neutre"
```

---

## Mise à jour Google Sheets après détection d'une réponse

Utiliser `connectors/gsheets.md` → **Endpoint 3** pour mettre à jour les colonnes :

| Colonne | Lettre | Valeur |
|---|---|---|
| `statut_lead` | T | `"Réponse positive"` / `"Réponse négative"` / `"Réponse neutre"` |
| `date_reponse` | AA | Date de la réponse (format `YYYY-MM-DD`) |
| `contenu_reponse` | AB | Corps nettoyé de l'email (20 lignes max) |
| `prochaine_action` | AF | `"Action manuelle requise"` si positif/neutre · `"Archiver"` si négatif |

```bash
# Exemple : mettre à jour les colonnes T, AA, AB, AF pour la ligne 5
curl -s -X PUT \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!T5:T5?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"values": [["Réponse positive"]]}'

curl -s -X PUT \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!AA5:AB5?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"values": [["2026-04-11", "Corps de la réponse ici..."]]}'

curl -s -X PUT \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!AF5?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"values": [["Action manuelle requise"]]}'
```

---

## Codes d'erreur courants

| Erreur | Cause | Action |
|---|---|---|
| `IMAP4.error: LOGIN failed` | Mauvais identifiants | Vérifier `imap_email` et `imap_password_var` dans `senders.json` + la valeur correspondante dans `.env` |
| `ConnectionRefusedError` | Mauvais host/port | Vérifier `imap_host` et `imap_port` dans `senders.json` (défaut : `imap.hostinger.com` / `993`) |
| `ssl.SSLError` | SSL non supporté | Utiliser `IMAP4_SSL` (déjà le cas ici) |
| `[AUTHENTICATIONFAILED]` | 2FA activé | Générer un mot de passe d'application dans hPanel Hostinger |

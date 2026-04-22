# Connecteur Google Sheets

## Présentation

Google Sheets est le système de tracking central de l'équipe de prospection. Toutes les lectures et écritures de leads passent exclusivement par ce connecteur.

---

## Configuration

```
SPREADSHEET_ID   : $GSHEETS_SPREADSHEET_ID  ← défini dans prospection-team/.env
SHEET_NAME       : $GSHEETS_SHEET_NAME        ← défini dans prospection-team/.env
SERVICE_ACCOUNT  : $GSHEETS_SERVICE_ACCOUNT_KEY ← chemin vers le fichier JSON de la clé
BASE_URL         : https://sheets.googleapis.com/v4/spreadsheets
```

> **Setup à faire une seule fois :**
> 1. Aller sur [console.cloud.google.com](https://console.cloud.google.com)
> 2. Créer un projet → activer l'API **Google Sheets**
> 3. Créer un **compte de service** → télécharger la clé JSON
> 4. Placer le fichier JSON dans `prospection-team/credentials/gsheets_key.json`
> 5. Ouvrir ton Google Sheet → Partager avec l'email du compte de service (éditeur)
> 6. Copier l'ID du Sheet depuis l'URL : `https://docs.google.com/spreadsheets/d/**{ID}**/edit`
> 7. Ajouter `GSHEETS_SPREADSHEET_ID={ID}` dans `.env`

---

## Authentification

Toutes les requêtes nécessitent un token OAuth 2.0 généré depuis la clé du compte de service.

```bash
# Générer le token d'accès (valable 1h — à régénérer si expiré)
set -a && source prospection-team/.env && set +a

TOKEN=$(python3 -c "
import json, time, jwt, requests
key = json.load(open('$GSHEETS_SERVICE_ACCOUNT_KEY'))
now = int(time.time())
claim = {
  'iss': key['client_email'],
  'scope': 'https://www.googleapis.com/auth/spreadsheets',
  'aud': 'https://oauth2.googleapis.com/token',
  'iat': now, 'exp': now + 3600
}
signed = jwt.encode(claim, key['private_key'], algorithm='RS256')
r = requests.post('https://oauth2.googleapis.com/token', data={
  'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
  'assertion': signed
})
print(r.json()['access_token'])
")
```

> ⚠️ Le token est temporaire. Ne jamais le stocker en clair — toujours le régénérer à chaque session.

---

## Endpoint 1 — Lire tous les leads `GET /values/{range}`

Utilisé par : Agent Sourcing (dédup), Agent Analyse & Relance, Agent Envoi

```bash
curl -s -X GET \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!A:AJ" \
  -H "Authorization: Bearer $TOKEN"
```

**Réponse :**
```json
{
  "values": [
    ["id_lead", "date_sourcing", "prenom", ...],  ← ligne 1 = en-têtes
    ["LEAD-005", "2026-04-03", "Aurelien", ...]   ← ligne 2+ = données
  ]
}
```

> Pour vérifier la déduplication : lire toutes les valeurs de la colonne `entreprise` (colonne H) et comparer avec le nouveau lead.

---

## Endpoint 2 — Ajouter un lead `POST /values/{range}:append`

Utilisé par : Agent ICP Score (ajout de tous les leads scorés)

```bash
curl -s -X POST \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!A1:append?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "values": [[
      "LEAD-XXX",       "2026-04-04",  "Prénom",      "Nom",
      "Poste",          "email@co.com","linkedin_url", "Entreprise",
      "Secteur",        "200",         "5000000",      "10 ans",
      "France",         "Paris",       "site.com",     "85",
      "HOT",            "À analyser",  "Signal détecté","Nouveau",
      "","","","","","0","","","","","","Envoyer email","2026-04-04","","",""
    ]]
  }'
```

> ⚠️ Respecter l'ordre exact des colonnes défini dans la ligne d'en-tête du Sheet.
> Les colonnes vides (non encore remplies) doivent être transmises comme `""`.

---

## Endpoint 3 — Mettre à jour une ligne `PUT /values/{range}`

Utilisé par : Agent Envoi (après envoi), Agent Analyse & Relance (après relance)

Pour mettre à jour une ligne, il faut d'abord connaître son numéro de ligne dans le Sheet (via Endpoint 1), puis cibler la plage exacte.

```bash
# Exemple : mettre à jour la ligne 3 (LEAD-005) après envoi du premier email
curl -s -X PUT \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!T3:X3?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "values": [[
      "Email envoyé",
      "2026-04-04",
      "Objet de l email envoyé",
      "Corps complet de l email",
      "messageId-brevo-retourné"
    ]]
  }'
```

> T = statut_lead · U = date_premier_contact · V = objet_email_envoye · W = corps_email · X = id_message_brevo

> Pour retrouver le numéro de ligne d'un lead : lire toutes les lignes (Endpoint 1) et chercher l'`id_lead` dans la colonne A. La position dans le tableau + 1 (pour l'en-tête) = numéro de ligne dans le Sheet.

---

## Endpoint 4 — Mettre à jour une cellule unique `PUT /values/{range}`

Pour des mises à jour ponctuelles (ex: date d'ouverture, nombre d'ouvertures, réponse).

```bash
# Exemple : logger une ouverture email pour la ligne 3
curl -s -X PUT \
  "https://sheets.googleapis.com/v4/spreadsheets/$GSHEETS_SPREADSHEET_ID/values/$GSHEETS_SHEET_NAME!Z3?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"values": [["2026-04-05"]]}'
```

---

## Colonnes du Sheet — Ordre exact

| # | Colonne | Lettre | Rempli par |
|---|---|---|---|
| 1 | id_lead | A | ICP Score |
| 2 | date_sourcing | B | ICP Score |
| 3 | prenom | C | ICP Score |
| 4 | nom | D | ICP Score |
| 5 | poste | E | ICP Score |
| 6 | email | F | ICP Score |
| 7 | linkedin | G | ICP Score |
| 8 | entreprise | H | ICP Score |
| 9 | secteur | I | ICP Score |
| 10 | taille_entreprise | J | ICP Score |
| 11 | ca_estime_eur | K | ICP Score |
| 12 | anciennete_entreprise | L | ICP Score |
| 13 | pays | M | ICP Score |
| 14 | ville | N | ICP Score |
| 15 | site_web | O | ICP Score |
| 16 | score_icp | P | ICP Score |
| 17 | statut_icp | Q | ICP Score |
| 18 | qualite_site_actuel | R | Enrichissement |
| 19 | signal_besoin_detecte | S | Enrichissement |
| 20 | statut_lead | T | ICP Score / Envoi |
| 21 | date_premier_contact | U | Envoi |
| 22 | objet_email_envoye | V | Enrichissement (rédigé) → Envoi (confirmé à l'envoi) |
| 23 | corps_email | W | Enrichissement |
| 24 | id_message_brevo | X | Envoi |
| 25 | date_ouverture | Y | ⚠️ Désactivé (pixels bloqués Gmail/Outlook) |
| 26 | nombre_ouvertures | Z | ⚠️ Désactivé (pixels bloqués Gmail/Outlook) |
| 27 | date_reponse | AA | Fetch Replies |
| 28 | contenu_reponse | AB | Fetch Replies |
| 29 | date_relance_1 | AC | Envoi |
| 30 | date_relance_2 | AD | Envoi |
| 31 | notes | AE | Manuel |
| 32 | prochaine_action | AF | Orchestrateur |
| 33 | date_prochaine_action | AG | Orchestrateur |
| 34 | corps_relance_1 | AH | Relance |
| 35 | corps_relance_2 | AI | Relance |
| 36 | **compte_envoi** | **AJ** | **Envoi** — email du sender qui a envoyé le 1er contact |

---

## Codes d'erreur courants

| Code | Cause | Action |
|---|---|---|
| 401 | Token expiré ou invalide | Régénérer le token (voir section Authentification) |
| 403 | Compte de service non partagé sur le Sheet | Partager le Sheet avec l'email du compte de service |
| 400 | Plage invalide ou colonne hors limites | Vérifier la lettre de colonne et le nom de l'onglet |
| 429 | Rate limit dépassé (300 req/min) | Attendre 60 secondes, réessayer |

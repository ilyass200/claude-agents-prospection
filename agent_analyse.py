#!/usr/bin/env python3
"""
Agent Fetch Replies → Agent Analyse
Pipeline : IMAP scan → update GSheets → calcul KPIs → rapport
"""
import imaplib, email as email_lib, json, time, requests, jwt, os, re
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv

load_dotenv('.env')

# ─── Config ───────────────────────────────────────────────────────────────────
BREVO_KEY  = os.getenv('BREVO_API_KEY')
SHEET_ID   = os.getenv('GSHEETS_SPREADSHEET_ID')
SHEET_NAME = os.getenv('GSHEETS_SHEET_NAME')
ICP_MIN    = int(os.getenv('ICP_SCORE_MINIMUM', 50))
R1_DELAI   = int(os.getenv('RELANCE_1_DELAI_JOURS', 4))
R2_DELAI   = int(os.getenv('RELANCE_2_DELAI_JOURS', 7))
SVC_KEY    = 'credentials/gsheets_key.json'
TODAY      = date.today()
TODAY_STR  = str(TODAY)

# ─── Senders avec mots de passe résolus ───────────────────────────────────────
with open('senders.json') as f:
    senders_cfg = json.load(f)

SENDERS = []
for s in senders_cfg['senders']:
    if not s.get('actif'):
        continue
    pw_var = s.get('imap_password_var', '')
    pw     = os.getenv(pw_var, '')
    if not pw:
        print(f'⚠️  Mot de passe IMAP manquant pour {s["email"]} (var: {pw_var}) — sender exclu')
        continue
    SENDERS.append({**s, 'imap_password': pw})

# ─── GSheets token ────────────────────────────────────────────────────────────
def get_token():
    key = json.load(open(SVC_KEY))
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
    return r.json()['access_token']

def col_idx(letter):
    idx = 0
    for c in letter.upper():
        idx = idx * 26 + (ord(c) - ord('A') + 1)
    return idx - 1

def get_cell(row, col_letter):
    i = col_idx(col_letter)
    return row[i] if i < len(row) else ''

def read_sheet(token):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{SHEET_NAME}!A:AJ'
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    rows = r.json().get('values', [])
    return rows[0] if rows else [], rows[1:] if len(rows) > 1 else []

def write_cells(row_num, updates, token):
    """updates = [(col_letter, value), ...]"""
    for col, val in updates:
        url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
               f'{SHEET_NAME}!{col}{row_num}?valueInputOption=USER_ENTERED')
        requests.put(url, json={'values': [[val]]},
                     headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})

def write_range_cells(row_num, start_col, values, token):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
           f'{SHEET_NAME}!{start_col}{row_num}?valueInputOption=USER_ENTERED')
    requests.put(url, json={'values': [values]},
                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})

# ─── IMAP helpers ─────────────────────────────────────────────────────────────
AUTORELY_SUBJECT_KW = [
    "absence", "absent", "out of office", "hors du bureau", "hors bureau",
    "réponse automatique", "automatic reply", "auto-reply", "autoreply",
    "vacation", "congé", "away", "unavailable", "indisponible",
]
AUTOREPLY_BODY_KW = [
    "je suis actuellement absent", "currently out of office", "out of the office",
    "hors du bureau", "hors de mon bureau", "en déplacement",
    "accès limité à mes courriels", "accès limité à mes emails", "limited access to my email",
    "absent jusqu'au", "absent du", "serai de retour", "will be back", "will return",
    "i'm out of office", "i am out of office", "i will be away", "i'm away",
    "réponse automatique", "automatic reply", "this is an automated",
    "je ne suis pas disponible", "je suis en congé", "je suis en vacances",
    "i'm on vacation", "i am on vacation", "en vacances jusqu",
    "pour toute urgence", "en cas d'urgence", "in case of emergency",
    "my out of office", "message automatique",
]

NEGATIVE_KW = ["pas intéressé", "non merci", "stop", "unsubscribe", "désinscription",
               "ne pas contacter", "remove", "opt out", "pas besoin", "pas de besoin",
               "sans suite", "pas de projet", "pas de budget"]
POSITIVE_KW = ["intéressé", "disponible", "oui", "appel", "rendez-vous", "quand",
               "calendly", "discuter", "15 minutes", "call", "me contacter",
               "contactez-moi", "appelez-moi", "n'hésitez pas", "avec plaisir",
               "pourquoi pas", "volontiers"]

def is_autoreply(subject, body):
    s = (subject or '').lower()
    b = (body or '').lower()
    for kw in AUTORELY_SUBJECT_KW:
        if kw in s:
            return True
    for kw in AUTOREPLY_BODY_KW:
        if kw in b:
            return True
    return False

def classify_reply(subject, body):
    # Auto-reply détectée en premier — priorité absolue
    if is_autoreply(subject, body):
        return "Réponse automatique"
    b = body.lower()
    for kw in NEGATIVE_KW:
        if kw in b:
            return "Réponse négative"
    for kw in POSITIVE_KW:
        if kw in b:
            return "Réponse positive"
    return "Réponse neutre"

def parse_imap_email(msg):
    subj_raw, enc = decode_header(msg.get('Subject') or '')[0]
    subject = subj_raw.decode(enc or 'utf-8') if isinstance(subj_raw, bytes) else (subj_raw or '')
    from_raw = msg.get('From', '')
    sender_email = parseaddr(from_raw)[1].lower().strip()
    date_str = msg.get('Date', '')
    try:
        dt = parsedate_to_datetime(date_str)
        date_fmt = dt.strftime('%Y-%m-%d')
    except Exception:
        date_fmt = TODAY_STR

    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
    else:
        if msg.get_content_type() == 'text/plain':
            charset = msg.get_content_charset() or 'utf-8'
            body = msg.get_payload(decode=True).decode(charset, errors='replace')

    lines = body.splitlines()
    clean = [l for l in lines if not l.strip().startswith('>') and l.strip()]
    clean_body = '\n'.join(clean[:20])
    return {'sender_email': sender_email, 'subject': subject, 'date': date_fmt, 'body': clean_body}

# ─── AGENT FETCH REPLIES ─────────────────────────────────────────────────────
def run_fetch_replies(token):
    print('\n' + '='*60)
    print('AGENT FETCH REPLIES')
    print('='*60)

    headers, rows = read_sheet(token)

    # Construire dict email_lead → {row_num, statut, date_reponse, compte_envoi}
    leads_by_email = {}
    for i, row in enumerate(rows):
        statut       = get_cell(row, 'T')
        date_reponse = get_cell(row, 'AA')
        email_lead   = get_cell(row, 'F').lower().strip()
        if not email_lead:
            continue
        # Exclure les leads déjà conclus
        if statut in ('Réponse positive', 'Réponse négative'):
            if date_reponse:  # déjà traité
                continue
        leads_by_email[email_lead] = {
            'row_num':      i + 2,
            'id_lead':      get_cell(row, 'A'),
            'prenom':       get_cell(row, 'C'),
            'nom':          get_cell(row, 'D'),
            'entreprise':   get_cell(row, 'H'),
            'statut':       statut,
            'date_reponse': date_reponse,
            'compte_envoi': get_cell(row, 'AJ'),
        }

    report = {
        'senders_scanned': 0,
        'emails_scanned': 0,
        'nouvelles_reponses': 0,
        'deja_traites': 0,
        'detail': [],
        'erreurs': []
    }

    for sender in SENDERS:
        print(f'\n  📬 Scan {sender["imap_email"]}...')
        try:
            imap = imaplib.IMAP4_SSL(sender['imap_host'], int(sender['imap_port']))
            imap.login(sender['imap_email'], sender['imap_password'])
            imap.select('INBOX')
        except Exception as e:
            msg = f'Connexion IMAP échouée pour {sender["imap_email"]} : {e}'
            print(f'  ❌ {msg}')
            report['erreurs'].append(msg)
            continue

        report['senders_scanned'] += 1

        # Fetch 30 derniers jours
        since_date = (date.today() - timedelta(days=30)).strftime('%d-%b-%Y')
        status, ids = imap.search(None, f'(SINCE "{since_date}")')
        msg_ids = ids[0].split() if status == 'OK' else []
        print(f'     {len(msg_ids)} emails dans la boîte')
        report['emails_scanned'] += len(msg_ids)

        sender_nouvelles = 0
        for mid in msg_ids:
            status2, data = imap.fetch(mid, '(RFC822)')
            if status2 != 'OK':
                continue
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)
            parsed = parse_imap_email(msg)

            prospect_email = parsed['sender_email']
            if prospect_email not in leads_by_email:
                continue

            lead = leads_by_email[prospect_email]

            # Déjà traité ?
            if lead['date_reponse']:
                report['deja_traites'] += 1
                continue

            # Classifier (sujet + corps)
            classification = classify_reply(parsed['subject'], parsed['body'])
            is_auto = (classification == 'Réponse automatique')

            # Mise à jour GSheets
            if is_auto:
                # Auto-reply : on log AA/AB mais on NE change PAS T (lead reste "Email envoyé")
                # AF = "Réponse automatique reçue" pour traçabilité
                write_cells(lead['row_num'], [('AF', 'Réponse automatique reçue')], token)
                write_range_cells(lead['row_num'], 'AA', [parsed['date'], '[AUTO] ' + parsed['body'][:490]], token)
            else:
                prochaine_action = 'Archiver' if classification == 'Réponse négative' else 'Action manuelle requise'
                write_cells(lead['row_num'], [('T', classification), ('AF', prochaine_action)], token)
                write_range_cells(lead['row_num'], 'AA', [parsed['date'], parsed['body'][:500]], token)

            # Marquer comme traité localement
            lead['date_reponse'] = parsed['date']
            lead['statut'] = lead['statut'] if is_auto else classification

            if not is_auto:
                report['nouvelles_reponses'] += 1
            sender_nouvelles += 1
            report['detail'].append({
                'lead':           f'{lead["prenom"]} {lead["nom"]}'.strip() or lead['entreprise'],
                'entreprise':     lead['entreprise'],
                'email':          prospect_email,
                'via_sender':     sender['id'],
                'classification': classification,
                'date':           parsed['date'],
                'extrait':        parsed['body'][:150]
            })
            icon = '🤖' if is_auto else '✅'
            print(f'  {icon} {lead["entreprise"]} — {classification}')

        imap.logout()
        print(f'     → {sender_nouvelles} nouvelle(s) réponse(s) traitée(s)')

    print(f'\n  Résumé Fetch Replies : {report["senders_scanned"]} senders scannés, '
          f'{report["emails_scanned"]} emails lus, {report["nouvelles_reponses"]} nouvelles réponses')

    return report, leads_by_email

# ─── AGENT ANALYSE ────────────────────────────────────────────────────────────
def run_analyse(token):
    print('\n' + '='*60)
    print('AGENT ANALYSE')
    print('='*60)

    headers, rows = read_sheet(token)

    # Structures
    total_envoyes    = 0
    reponses_pos     = []
    reponses_neg     = []
    reponses_neutres = []
    reponses_auto    = []   # auto-replies — exclus du taux de réponse
    a_relancer_1     = []
    a_relancer_2     = []
    froids           = []
    erreurs_envoi    = []
    nouveaux         = []
    stats_secteur    = {}
    stats_sender     = {}

    for i, row in enumerate(rows):
        statut          = get_cell(row, 'T')
        email           = get_cell(row, 'F')
        prenom          = get_cell(row, 'C')
        nom             = get_cell(row, 'D')
        entreprise      = get_cell(row, 'H')
        secteur         = get_cell(row, 'I')
        score_str       = get_cell(row, 'P')
        statut_icp      = get_cell(row, 'Q')
        date_contact    = get_cell(row, 'U')
        date_relance_1  = get_cell(row, 'AC')
        date_relance_2  = get_cell(row, 'AD')
        compte_envoi    = get_cell(row, 'AJ')
        date_reponse    = get_cell(row, 'AA')
        contenu_rep     = get_cell(row, 'AB')
        id_lead         = get_cell(row, 'A')
        row_num         = i + 2

        name = f'{prenom} {nom}'.strip() or entreprise

        # Stats secteur
        if secteur and statut == 'Email envoyé' or statut in ('Réponse positive', 'Réponse négative', 'Réponse neutre'):
            if secteur not in stats_secteur:
                stats_secteur[secteur] = {'envoyes': 0, 'reponses': 0}

        # Comptage des envoyés
        if statut in ('Email envoyé', 'Réponse positive', 'Réponse négative', 'Réponse neutre', 'En cours d\'envoi'):
            if date_contact:
                total_envoyes += 1
                if secteur:
                    stats_secteur.setdefault(secteur, {'envoyes': 0, 'reponses': 0})
                    stats_secteur[secteur]['envoyes'] += 1
                if compte_envoi:
                    stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                    stats_sender[compte_envoi]['envoyes'] += 1

        # Réponses
        if statut == 'Réponse positive':
            reponses_pos.append({'name': name, 'entreprise': entreprise, 'email': email,
                                  'score': score_str, 'extrait': contenu_rep[:100], 'id': id_lead})
            if secteur:
                stats_secteur.setdefault(secteur, {'envoyes': 0, 'reponses': 0})
                stats_secteur[secteur]['reponses'] += 1
            if compte_envoi:
                stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                stats_sender[compte_envoi]['reponses'] += 1

        elif statut == 'Réponse négative':
            reponses_neg.append({'name': name, 'entreprise': entreprise})
            if secteur:
                stats_secteur.setdefault(secteur, {'envoyes': 0, 'reponses': 0})
                stats_secteur[secteur]['reponses'] += 1
            if compte_envoi:
                stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                stats_sender[compte_envoi]['reponses'] += 1

        elif statut == 'Réponse neutre':
            # Re-vérifier : auto-reply mal classée avant la correction ?
            if contenu_rep.startswith('[AUTO]') or is_autoreply('', contenu_rep):
                reponses_auto.append({'name': name, 'entreprise': entreprise,
                                       'extrait': contenu_rep[:80], 'id': id_lead})
            else:
                reponses_neutres.append({'name': name, 'entreprise': entreprise,
                                          'extrait': contenu_rep[:100], 'id': id_lead})
                if secteur:
                    stats_secteur.setdefault(secteur, {'envoyes': 0, 'reponses': 0})
                    stats_secteur[secteur]['reponses'] += 1
                if compte_envoi:
                    stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                    stats_sender[compte_envoi]['reponses'] += 1

        # Leads éligibles à relance — inclut aussi "Réponse automatique" (statut T intact = "Email envoyé")
        # Note : les auto-replies enregistrent date_reponse en AA mais laissent T="Email envoyé"
        # Donc ils tombent dans le elif "Email envoyé" ci-dessous, ce qui est correct.

        elif statut == 'Email envoyé' and date_contact:
            # Détecter si une auto-reply a été reçue (AA renseignée, contenu commence par [AUTO])
            if date_reponse and contenu_rep.startswith('[AUTO]'):
                reponses_auto.append({'name': name, 'entreprise': entreprise,
                                       'extrait': contenu_rep[7:80], 'id': id_lead})
            try:
                d_contact = date.fromisoformat(date_contact[:10])
            except Exception:
                continue

            jours_depuis_contact = (TODAY - d_contact).days

            if not date_relance_1:
                # Éligible relance 1 si > R1_DELAI jours depuis envoi
                if jours_depuis_contact >= R1_DELAI:
                    a_relancer_1.append({
                        'name': name, 'entreprise': entreprise, 'email': email,
                        'row': row_num, 'id': id_lead, 'compte_envoi': compte_envoi,
                        'date_contact': date_contact[:10],
                        'jours': jours_depuis_contact
                    })
                    if compte_envoi:
                        stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                        stats_sender[compte_envoi]['relances_1'] += 1
            elif not date_relance_2:
                # Éligible relance 2 si > R2_DELAI jours depuis relance 1
                try:
                    d_r1 = date.fromisoformat(date_relance_1[:10])
                    jours_depuis_r1 = (TODAY - d_r1).days
                    if jours_depuis_r1 >= R2_DELAI:
                        a_relancer_2.append({
                            'name': name, 'entreprise': entreprise, 'email': email,
                            'row': row_num, 'id': id_lead, 'compte_envoi': compte_envoi,
                            'date_relance_1': date_relance_1[:10],
                            'jours': jours_depuis_r1
                        })
                        if compte_envoi:
                            stats_sender.setdefault(compte_envoi, {'envoyes': 0, 'reponses': 0, 'relances_1': 0, 'relances_2': 0})
                            stats_sender[compte_envoi]['relances_2'] += 1
                except Exception:
                    pass
            else:
                # 2 relances épuisées → froid
                froids.append({'name': name, 'entreprise': entreprise})

        elif statut == 'Nouveau':
            nouveaux.append({'id': id_lead, 'entreprise': entreprise})

        elif statut == 'Erreur envoi':
            erreurs_envoi.append({'id': id_lead, 'entreprise': entreprise, 'email': email})

    # ─── Calcul KPIs — auto-replies exclus ───────────────────────────────────
    total_reponses = len(reponses_pos) + len(reponses_neg) + len(reponses_neutres)
    taux_rep   = round(total_reponses / total_envoyes * 100, 1) if total_envoyes else 0
    taux_conv  = round(len(reponses_pos) / total_envoyes * 100, 1) if total_envoyes else 0

    # ─── Affichage rapport ────────────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           RAPPORT ANALYSE — {TODAY_STR}             ║
╚══════════════════════════════════════════════════════════╝

━━━ VUE D'ENSEMBLE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total emails envoyés    : {total_envoyes}
  Réponses reçues         : {total_reponses} ({taux_rep}%)  ← hors réponses automatiques
    → Positives           : {len(reponses_pos)}
    → Neutres             : {len(reponses_neutres)}
    → Négatives           : {len(reponses_neg)}
  Réponses automatiques   : {len(reponses_auto)} (ignorées — leads toujours relançables)
  Taux de conversion (RDV): {taux_conv}%
  En attente (Nouveau)    : {len(nouveaux)}
  Erreurs envoi           : {len(erreurs_envoi)}
""")

    if reponses_pos:
        print('━━━ 🟢 LEADS CHAUDS — traiter en priorité ━━━━━━━━━━━━━━━')
        for l in reponses_pos:
            print(f'  {l["id"]} | {l["entreprise"][:35]} | Score: {l["score"]}')
            if l['extrait']:
                print(f'    Réponse: "{l["extrait"][:80]}..."')
        print()

    if reponses_auto:
        print(f'━━━ 🤖 RÉPONSES AUTOMATIQUES ({len(reponses_auto)}) — exclues du taux ━━━━━━━━')
        for l in reponses_auto:
            print(f'  {l["id"]} | {l["entreprise"][:40]} — toujours relançable')
        print()

    if reponses_neutres:
        print('━━━ 🟡 RÉPONSES NEUTRES — à qualifier ━━━━━━━━━━━━━━━━━━')
        for l in reponses_neutres:
            print(f'  {l["id"]} | {l["entreprise"][:35]}')
            if l['extrait']:
                print(f'    Réponse: "{l["extrait"][:80]}..."')
        print()

    if a_relancer_1:
        print(f'━━━ 🔁 RELANCE 1 ÉLIGIBLES ({len(a_relancer_1)} leads) ━━━━━━━━━━━━━━━')
        for l in a_relancer_1[:15]:
            print(f'  {l["id"]} | {l["entreprise"][:35]} | {l["jours"]}j depuis envoi | via {l["compte_envoi"]}')
        if len(a_relancer_1) > 15:
            print(f'  ... et {len(a_relancer_1) - 15} autres')
        print()

    if a_relancer_2:
        print(f'━━━ 🔁 RELANCE 2 ÉLIGIBLES ({len(a_relancer_2)} leads) ━━━━━━━━━━━━━━━')
        for l in a_relancer_2[:10]:
            print(f'  {l["id"]} | {l["entreprise"][:35]} | {l["jours"]}j depuis relance 1 | via {l["compte_envoi"]}')
        print()

    if froids:
        print(f'━━━ 🧊 LEADS FROIDS — 2 relances épuisées ({len(froids)}) ━━━━━━━━━')
        for l in froids[:10]:
            print(f'  {l["entreprise"][:35]}')
        print()

    # Stats secteur
    if stats_secteur:
        print('━━━ PERFORMANCE PAR SECTEUR ━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'  {"Secteur":<30} {"Envoyés":>8} {"Réponses":>9} {"Taux":>6}')
        print('  ' + '-'*56)
        for sec, s in sorted(stats_secteur.items(), key=lambda x: -x[1]['envoyes']):
            taux = round(s['reponses'] / s['envoyes'] * 100, 1) if s['envoyes'] else 0
            print(f'  {sec[:30]:<30} {s["envoyes"]:>8} {s["reponses"]:>9} {taux:>5}%')
        print()

    # Stats sender
    if stats_sender:
        print('━━━ PERFORMANCE PAR SENDER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'  {"Sender":<30} {"Envoyés":>8} {"Réponses":>9} {"Taux":>6} {"R1 att.":>8} {"R2 att.":>8}')
        print('  ' + '-'*72)
        for sd, s in stats_sender.items():
            taux = round(s['reponses'] / s['envoyes'] * 100, 1) if s['envoyes'] else 0
            print(f'  {sd[:30]:<30} {s["envoyes"]:>8} {s["reponses"]:>9} {taux:>5}% {s["relances_1"]:>8} {s["relances_2"]:>8}')
        print()

    # Recommandations
    print('━━━ RECOMMANDATIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    if reponses_pos:
        print(f'  → {len(reponses_pos)} lead(s) chaud(s) à traiter manuellement — répondre rapidement')
    if a_relancer_1:
        print(f'  → {len(a_relancer_1)} lead(s) éligibles à la relance 1 — lance "prépare les relances"')
    if a_relancer_2:
        print(f'  → {len(a_relancer_2)} lead(s) éligibles à la relance 2')
    if total_envoyes > 0 and total_reponses == 0:
        print(f'  → Aucune réponse encore — normal si les emails ont été envoyés aujourd\'hui')
    if erreurs_envoi:
        print(f'  → {len(erreurs_envoi)} email(s) en erreur à investiguer')
    if len(nouveaux) > 0:
        print(f'  → {len(nouveaux)} lead(s) "Nouveau" non encore envoyés dans le sheet')

    print()
    return {
        'total_envoyes': total_envoyes,
        'taux_reponse': taux_rep,
        'reponses_pos': len(reponses_pos),
        'a_relancer_1': len(a_relancer_1),
        'a_relancer_2': len(a_relancer_2),
    }

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    token = get_token()
    print('✅ Token GSheets obtenu')

    fetch_report, _ = run_fetch_replies(token)
    run_analyse(token)

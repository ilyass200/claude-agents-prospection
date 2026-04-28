#!/usr/bin/env python3
"""
Agent Envoi — Programmation des emails via Brevo
Pipeline : Vérif statut → Vérif Brevo → Blacklist → Contenu → Lock → scheduledAt → Envoi → Sheet
"""
import json, time, requests, jwt, os, re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv('.env')

# ─── Config ───────────────────────────────────────────────────────────────────
BREVO_KEY   = os.getenv('BREVO_API_KEY')
SHEET_ID    = os.getenv('GSHEETS_SPREADSHEET_ID')
SHEET_NAME  = os.getenv('GSHEETS_SHEET_NAME')
ICP_MIN     = int(os.getenv('ICP_SCORE_MINIMUM', 50))
SEND_TIME   = os.getenv('SEND_TIME', '09:00:00+02:00')
DELAY_MIN   = int(os.getenv('EMAIL_DELAY_MINUTES', 3))
SVC_KEY     = 'credentials/gsheets_key.json'

TZ_PARIS    = timezone(timedelta(hours=2))
NOW_PARIS   = datetime.now(TZ_PARIS)

# ─── Senders ──────────────────────────────────────────────────────────────────
with open('senders.json') as f:
    senders_cfg = json.load(f)
SENDERS = [s for s in senders_cfg['senders'] if s.get('actif')]

# ─── Calcul scheduledAt de base ───────────────────────────────────────────────
def base_scheduled_at():
    """Retourne la base du planning. Toujours aujourd'hui à SEND_TIME."""
    hms, offset = SEND_TIME.rsplit('+', 1) if '+' in SEND_TIME else (SEND_TIME, '00:00')
    h, m, s = map(int, hms.split(':'))
    tz_offset = timedelta(hours=int(offset.split(':')[0]), minutes=int(offset.split(':')[1]))
    tz = timezone(tz_offset)
    today = NOW_PARIS.date()
    base = datetime(today.year, today.month, today.day, h, m, s, tzinfo=tz)
    # Si on est déjà passé l'heure d'envoi, utiliser maintenant + 5 min
    if NOW_PARIS >= base:
        base = NOW_PARIS.replace(second=0, microsecond=0) + timedelta(minutes=5)
    return base

BASE_TIME = base_scheduled_at()
print(f'Heure de base d\'envoi : {BASE_TIME.strftime("%Y-%m-%dT%H:%M:%S%z")}')

# ─── GSheets auth ─────────────────────────────────────────────────────────────
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

def refresh_token_if_needed(token_info):
    """Re-génère le token si plus de 50 minutes se sont écoulées."""
    if (time.time() - token_info['generated_at']) > 3000:
        token_info['token'] = get_token()
        token_info['generated_at'] = time.time()
        print('  🔄 Token GSheets renouvelé')
    return token_info['token']

# ─── Lecture sheet ─────────────────────────────────────────────────────────────
def read_all_rows(token):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{SHEET_NAME}!A:AJ'
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    data = r.json()
    rows = data.get('values', [])
    if not rows:
        return [], []
    headers = rows[0]
    return headers, rows[1:]

def col_index(headers, letter):
    """Retourne l'index 0-based d'une colonne par sa lettre (A=0, B=1, ...)"""
    idx = 0
    for c in letter.upper():
        idx = idx * 26 + (ord(c) - ord('A') + 1)
    return idx - 1

def get_cell(row, headers, letter):
    idx = col_index(headers, letter)
    if idx < len(row):
        return row[idx]
    return ''

# ─── Quota checker ─────────────────────────────────────────────────────────────
def compute_quota(headers, rows, today_str):
    """Calcule combien d'emails chaque sender a déjà envoyé aujourd'hui."""
    quota = {s['id']: s['max_emails_par_jour'] for s in SENDERS}
    sent_today = {s['id']: 0 for s in SENDERS}
    for row in rows:
        date_contact = get_cell(row, headers, 'U')
        compte_envoi = get_cell(row, headers, 'AJ')
        if date_contact.startswith(today_str) and compte_envoi:
            for s in SENDERS:
                if s['email'] == compte_envoi:
                    sent_today[s['id']] += 1
    restant = {sid: quota[sid] - sent_today[sid] for sid in quota}
    return restant

def pick_sender(quota_restant):
    """Round-robin : choisit le sender avec le plus grand quota restant."""
    eligible = [(s, quota_restant[s['id']]) for s in SENDERS if quota_restant.get(s['id'], 0) > 0]
    if not eligible:
        return None
    eligible.sort(key=lambda x: -x[1])
    return eligible[0][0]

# ─── Brevo checks ─────────────────────────────────────────────────────────────
def brevo_already_contacted(email):
    url = f'https://api.brevo.com/v3/smtp/emails?email={quote(email)}&limit=1&sort=desc'
    r = requests.get(url, headers={'api-key': BREVO_KEY})
    if r.status_code >= 500:
        return False  # Continuer quand même
    data = r.json()
    return bool(data.get('transactionalEmails'))

def brevo_is_blacklisted(email):
    url = f'https://api.brevo.com/v3/contacts/{quote(email)}'
    r = requests.get(url, headers={'api-key': BREVO_KEY})
    if r.status_code == 404:
        return False  # Inconnu, pas blacklisté
    if r.status_code >= 500:
        return False  # Continuer quand même
    if r.status_code == 200:
        return r.json().get('emailBlacklisted', False)
    return False

# ─── Sheet writes ─────────────────────────────────────────────────────────────
def write_cell(row_num, col_letter, value, token):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
           f'{SHEET_NAME}!{col_letter}{row_num}?valueInputOption=USER_ENTERED')
    requests.put(url,
                 json={'values': [[value]]},
                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})

def write_range(row_num, start_col, values, token):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
           f'{SHEET_NAME}!{start_col}{row_num}?valueInputOption=USER_ENTERED')
    requests.put(url,
                 json={'values': [values]},
                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})

# ─── Brevo send ───────────────────────────────────────────────────────────────
def brevo_send(sender, to_email, to_name, subject, body_text, scheduled_at):
    text_with_sig = (
        f"{body_text}\n\n"
        f"--\n"
        f"{sender['name']}\n"
        f"{sender['title']}\n"
        f"{sender['website']}"
    )
    payload = {
        'sender':       {'name': sender['name'], 'email': sender['email']},
        'to':           [{'email': to_email, 'name': to_name}],
        'subject':      subject,
        'textContent':  text_with_sig,
        'scheduledAt':  scheduled_at.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
    }
    r = requests.post('https://api.brevo.com/v3/smtp/email',
                      json=payload,
                      headers={'api-key': BREVO_KEY, 'Content-Type': 'application/json'})
    return r.status_code, r.json()

# ─── Main ────────────────────────────────────────────────────────────────────
def run():
    print('='*65)
    print('AGENT ENVOI — Programmation emails du 28/04/2026')
    print('='*65)

    token_info = {'token': get_token(), 'generated_at': time.time()}
    token = token_info['token']
    print('✅ Token GSheets obtenu')

    headers, rows = read_all_rows(token)
    today_str = NOW_PARIS.strftime('%Y-%m-%d')
    quota_restant = compute_quota(headers, rows, today_str)

    for s in SENDERS:
        print(f'   Sender {s["email"]} — quota restant : {quota_restant[s["id"]]}/{s["max_emails_par_jour"]}')

    # Compteurs d'envoi par sender pour le calcul scheduledAt
    counters  = {s['id']: 0 for s in SENDERS}
    # Stats
    envoyes   = 0
    skips     = {'deja_contacte': 0, 'blacklist': 0, 'invalide': 0, 'statut': 0, 'score': 0, 'quota': 0}
    echecs    = 0
    detail    = []

    # Filtrer les leads statut "Nouveau"
    nouveaux = []
    for i, row in enumerate(rows):
        statut = get_cell(row, headers, 'T')
        if statut == 'Nouveau':
            nouveaux.append((i + 2, row))  # +2 = 1 header + 1-indexed

    print(f'\n📋 Leads "Nouveau" trouvés : {len(nouveaux)}')
    print(f'📨 Quota total disponible  : {sum(quota_restant.values())} emails\n')

    if not nouveaux:
        print('⚠️  Aucun lead à envoyer.')
        return

    for row_num, row in nouveaux:
        token = refresh_token_if_needed(token_info)
        lead_id    = get_cell(row, headers, 'A')
        prenom     = get_cell(row, headers, 'C')
        nom        = get_cell(row, headers, 'D')
        email      = get_cell(row, headers, 'F').strip()
        entreprise = get_cell(row, headers, 'H')
        score_str  = get_cell(row, headers, 'P')
        objet      = get_cell(row, headers, 'V').strip()
        corps      = get_cell(row, headers, 'W').strip()

        to_name = f'{prenom} {nom}'.strip() or entreprise

        # ÉTAPE 1 — Vérifier statut en temps réel
        # (On relit depuis le cache déjà chargé, suffisant ici)
        statut_actuel = get_cell(row, headers, 'T')
        if statut_actuel != 'Nouveau':
            skips['statut'] += 1
            continue

        # ÉTAPE 2 — Brevo history
        if brevo_already_contacted(email):
            write_cell(row_num, 'T', 'Déjà contacté', token)
            skips['deja_contacte'] += 1
            detail.append({'id_lead': lead_id, 'email': email, 'statut': 'Déjà contacté'})
            print(f'  ⏭️  {lead_id} ({entreprise}) — Déjà contacté Brevo')
            continue

        # ÉTAPE 3 — Blacklist
        if brevo_is_blacklisted(email):
            write_cell(row_num, 'T', 'Bloqué — blacklist', token)
            skips['blacklist'] += 1
            detail.append({'id_lead': lead_id, 'email': email, 'statut': 'Bloqué — blacklist'})
            print(f'  ⛔ {lead_id} ({entreprise}) — Blacklisté')
            continue

        # ÉTAPE 4 — Vérifier contenu
        try:
            score = int(score_str)
        except (ValueError, TypeError):
            score = 0
        if not email or not objet or not corps or score < ICP_MIN:
            reason = 'Email invalide' if (not email or not objet or not corps) else 'Score insuffisant'
            write_cell(row_num, 'T', reason, token)
            skips['invalide'] += 1
            detail.append({'id_lead': lead_id, 'email': email, 'statut': reason})
            print(f'  ❌ {lead_id} ({entreprise}) — {reason}')
            continue

        # Sélectionner sender
        sender = pick_sender(quota_restant)
        if not sender:
            print('\n⚠️  Tous les senders ont atteint leur quota journalier. Arrêt.')
            skips['quota'] += (len(nouveaux) - envoyes - sum(skips.values()))
            break

        # ÉTAPE 5 — Verrouillage
        write_cell(row_num, 'T', 'En cours d\'envoi', token)

        # ÉTAPE 6 — scheduledAt
        count = counters[sender['id']]
        scheduled_at = BASE_TIME + timedelta(minutes=count * DELAY_MIN)

        # ÉTAPE 7 — Envoi Brevo
        status_code, resp = brevo_send(sender, email, to_name, objet, corps, scheduled_at)
        scheduled_str = scheduled_at.strftime('%Y-%m-%dT%H:%M:%S+02:00')

        if status_code in (200, 201, 202):
            msg_id = resp.get('messageId', '')
            counters[sender['id']] += 1
            quota_restant[sender['id']] -= 1
            envoyes += 1

            # ÉTAPE 8 — Mise à jour sheet — PUT 1 (T:X)
            write_range(row_num, 'T', [
                'Email envoyé',
                scheduled_str,
                objet,
                corps,
                msg_id
            ], token)
            # PUT 2 — AJ : compte_envoi
            write_cell(row_num, 'AJ', sender['email'], token)

            detail.append({
                'id_lead':     lead_id,
                'email':       email,
                'sender':      sender['email'],
                'scheduled':   scheduled_str,
                'msg_id':      msg_id,
                'statut':      'Envoyé'
            })
            print(f'  ✅ [{envoyes:3d}] {lead_id} — {entreprise[:35]} → {sender["email"]} @ {scheduled_at.strftime("%H:%M")}')

        else:
            # Erreur 4xx/5xx — réessayer une fois si 5xx
            if status_code >= 500:
                time.sleep(60)
                status_code2, resp2 = brevo_send(sender, email, to_name, objet, corps, scheduled_at)
                if status_code2 in (200, 201, 202):
                    msg_id = resp2.get('messageId', '')
                    counters[sender['id']] += 1
                    quota_restant[sender['id']] -= 1
                    envoyes += 1
                    write_range(row_num, 'T', ['Email envoyé', scheduled_str, objet, corps, msg_id], token)
                    write_cell(row_num, 'AJ', sender['email'], token)
                    print(f'  ✅ [{envoyes:3d}] {lead_id} — {entreprise[:35]} (retry) → {sender["email"]} @ {scheduled_at.strftime("%H:%M")}')
                    detail.append({'id_lead': lead_id, 'email': email, 'sender': sender['email'], 'scheduled': scheduled_str, 'statut': 'Envoyé (retry)'})
                    continue

            write_cell(row_num, 'T', 'Erreur envoi', token)
            echecs += 1
            detail.append({'id_lead': lead_id, 'email': email, 'statut': f'Erreur {status_code}', 'detail': str(resp)})
            print(f'  ❌ {lead_id} ({entreprise}) — Erreur {status_code}: {str(resp)[:100]}')

        time.sleep(0.3)  # anti rate-limit API Brevo

    # ─── Rapport ─────────────────────────────────────────────────────────────
    print('\n' + '='*65)
    print('RAPPORT ENVOI — 2026-04-28')
    print('='*65)
    print(f'✅ Emails programmés : {envoyes}')
    print(f'❌ Échecs            : {echecs}')
    print(f'⏭️  Skippés           : {sum(skips.values())} (déjà contactés: {skips["deja_contacte"]}, blacklist: {skips["blacklist"]}, invalide: {skips["invalide"]}, quota: {skips["quota"]})')
    print()
    print('Quota final par sender :')
    for s in SENDERS:
        envoyes_s = counters[s['id']]
        restant   = quota_restant[s['id']]
        print(f'  {s["email"]} → {envoyes_s} envoyés ce jour | {restant} restants')

    # Planning résumé
    for s in SENDERS:
        if counters[s['id']] > 0:
            t_start = BASE_TIME
            t_end   = BASE_TIME + timedelta(minutes=(counters[s['id']] - 1) * DELAY_MIN)
            print(f'\n  📅 {s["email"]} : {t_start.strftime("%H:%M")} → {t_end.strftime("%H:%M")} '
                  f'({counters[s["id"]]} emails, 1 toutes les {DELAY_MIN} min)')

if __name__ == '__main__':
    run()

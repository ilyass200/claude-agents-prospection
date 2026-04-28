#!/usr/bin/env python3
"""
Pipeline Sourcing — 100 nouveaux leads qualifiés
Orchestrateur → Sourcing → ICP Score → Enrichissement → GSheets
"""
import json, time, requests, jwt, os, math, random, re
from datetime import date
from dotenv import load_dotenv

load_dotenv('.env')

# ─── Config ───────────────────────────────────────────────────────────────────
APOLLO_KEY  = os.getenv('APOLLO_API_KEY')
SHEET_ID    = os.getenv('GSHEETS_SPREADSHEET_ID')
SHEET_NAME  = os.getenv('GSHEETS_SHEET_NAME')
SVC_KEY     = 'credentials/gsheets_key.json'
ICP_MIN     = int(os.getenv('ICP_SCORE_MINIMUM', 50))
CA_MIN      = int(os.getenv('CA_MINIMUM', 500000))
TARGET      = 100
TODAY       = str(date.today())
START_ID    = 663  # LEAD-662 est le dernier

# ─── Secteurs (priority order) ───────────────────────────────────────────────
SECTORS = [
    ('5567cd477369645401010000', 'Immobilier',           25, 'immobilier'),
    ('5567ce9d7369643bc19c0000', 'Hôtellerie',           25, 'hotellerie'),
    ('5567e0e0736964198de70700', 'Restauration',         25, 'restauration'),
    ('5567cda97369644cfd3e0000', 'Luxe & Bijouterie',    25, 'luxe'),
    ('5567cdd47369643dbf260000', 'Conseil & Management', 20, 'conseil'),
    ('5567ce1f7369643b78570000', 'Expertise comptable',  20, 'liberal'),
    ('5567ced173696450cb580000', 'Retail',               20, 'ecommerce'),
    ('5567e19c7369641c48e70100', 'E-learning',           15, 'formation'),
    ('5567cd49736964541d010000', 'Formation & Coaching', 15, 'formation'),
]

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

# ─── Read existing companies ──────────────────────────────────────────────────
def read_existing(token):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{SHEET_NAME}!A:H'
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    rows = r.json().get('values', [])
    companies = set()
    last_id = 662
    for row in rows[1:]:
        if len(row) > 7 and row[7]:
            companies.add(row[7].lower().strip())
        if len(row) > 0 and row[0]:
            m = re.search(r'LEAD-(\d+)', row[0])
            if m:
                last_id = max(last_id, int(m.group(1)))
    return companies, last_id

# ─── Apollo search ────────────────────────────────────────────────────────────
def apollo_search(tag_id, page=1, per_page=25):
    url = 'https://api.apollo.io/api/v1/mixed_people/api_search'
    headers = {'Content-Type': 'application/json', 'X-Api-Key': APOLLO_KEY}
    body = {
        'person_titles': [
            'CEO', 'Founder', 'Co-Founder', 'PDG',
            'Directeur Général', 'DG', 'Gérant', 'Président',
            'Directeur', 'Fondateur', 'Associé', 'Managing Director'
        ],
        'person_locations': ['France'],
        'organization_num_employees_ranges': ['15,500'],
        'organization_industry_tag_ids': [tag_id],
        'reveal_personal_emails': False,
        'reveal_phone_number': False,
        'page': page,
        'per_page': per_page
    }
    r = requests.post(url, json=body, headers=headers)
    if r.status_code == 429:
        print('  ⚠️  Rate limit Apollo — attente 60s')
        time.sleep(60)
        r = requests.post(url, json=body, headers=headers)
    if r.status_code != 200:
        print(f'  ❌ Apollo search error {r.status_code}: {r.text[:200]}')
        return []
    data = r.json()
    return data.get('people', [])

# ─── Apollo reveal ────────────────────────────────────────────────────────────
def reveal_contact(apollo_id):
    url = 'https://api.apollo.io/api/v1/people/match'
    headers = {'Content-Type': 'application/json', 'X-Api-Key': APOLLO_KEY}
    body = {'id': apollo_id, 'reveal_personal_emails': False}
    r = requests.post(url, json=body, headers=headers)
    if r.status_code == 429:
        print('  ⚠️  Rate limit Apollo — attente 60s')
        time.sleep(60)
        r = requests.post(url, json=body, headers=headers)
    if r.status_code != 200:
        return None
    return r.json().get('person')

# ─── ICP Scoring ──────────────────────────────────────────────────────────────
def score_icp(person, sector_score):
    detail = {'budget': 0, 'secteur': sector_score, 'besoin': 0, 'anciennete': 0, 'bonus': 0}

    org = (person.get('organization') or {})
    num_emp    = org.get('estimated_num_employees', 0) or 0
    annual_rev = org.get('annual_revenue', 0) or 0
    founded_yr = org.get('founded_year', None)
    website    = (org.get('website_url') or '').strip()

    # Critère 1 — Budget
    if annual_rev >= 1_000_000:
        detail['budget'] = 40
    elif annual_rev >= 500_000:
        detail['budget'] = 25
    elif annual_rev >= 200_000:
        detail['budget'] = 10
    elif annual_rev == 0 and num_emp > 0:
        if num_emp >= 50:
            detail['budget'] = 40
        elif num_emp >= 20:
            detail['budget'] = 25
        elif num_emp >= 10:
            detail['budget'] = 10

    # Critère 3 — Besoin détecté
    if not website:
        detail['besoin'] = 25   # Pas de site web
    else:
        detail['besoin'] = 10   # Site présent, assume basique/à améliorer

    # Critère 4 — Ancienneté
    if founded_yr:
        age = 2026 - int(founded_yr)
        if age >= 5:
            detail['anciennete'] = 10
        elif age >= 2:
            detail['anciennete'] = 7
        elif age >= 1:
            detail['anciennete'] = 0
        else:
            detail['anciennete'] = -20
    else:
        detail['anciennete'] = 7  # Inconnu → conserateur

    total = sum(detail.values())
    total = max(0, min(115, total))
    score = round(total * 100 / 115)

    if score >= 80:   statut = 'HOT'
    elif score >= 70: statut = 'WARM'
    elif score >= 50: statut = 'TIÈDE'
    else:             statut = 'COLD'

    return score, statut, detail

# ─── Email templates ──────────────────────────────────────────────────────────
EMAIL_TEMPLATES = {
    'immobilier': {
        'objets': [
            'PROPOSITION — Vitrine digitale sur mesure · {entreprise}',
            'Suggestion — Repositionner la présence digitale de {entreprise}',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "{entreprise} a un positionnement haut de gamme — mais votre site actuel ne retranscrit pas encore ce niveau. "
            "C'est souvent là que se perdent vos prospects les plus qualifiés, avant même le premier contact.\n\n"
            "Un site conçu à la hauteur de vos biens peut changer ça : il installe la confiance dès les premières secondes "
            "et filtre naturellement vers une clientèle sérieuse.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des sites Webflow sur mesure "
            "pour les acteurs de l'immobilier premium qui refusent le compromis entre image et positionnement réel.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de présence digitale — or dans l'immobilier, vos clients qualifiés cherchent en ligne "
            "avant tout autre démarche. Sans site, vous perdez ces prospects avant même qu'ils puissent vous contacter.\n\n"
            "Un site sur mesure peut devenir votre meilleur outil de qualification : présence crédible, confiance instantanée, "
            "contacts entrants ciblés.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow, je conçois des vitrines "
            "digitales premium pour les professionnels de l'immobilier.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
    },
    'hotellerie': {
        'objets': [
            'PROPOSITION — Site sur mesure pour {entreprise}',
            'Suggestion — La présence digitale de {entreprise} à la hauteur de votre établissement',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "L'expérience {entreprise} est soignée — mais votre site actuel ne retranscrit pas encore ce niveau. "
            "Un client haut de gamme décide de réserver en quelques secondes, bien avant de vous appeler, "
            "et un site qui ne donne pas envie coûte des réservations.\n\n"
            "Un site repensé sur mesure peut devenir votre meilleur outil de conversion : il crée l'envie avant même l'arrivée.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des expériences digitales "
            "pour les établissements qui veulent que leur site soit à la hauteur de ce qu'ils offrent.\n\n"
            "Auriez-vous 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de présence digitale — pourtant, la décision de réservation commence en ligne. "
            "Sans site, vos clients potentiels vont chez un concurrent qui, lui, a une vitrine à la hauteur.\n\n"
            "Un site sur mesure peut devenir le premier service que vous rendez à vos clients : il crée l'envie avant même l'arrivée.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, "
            "je conçois des sites pour les acteurs de l'hôtellerie et de la restauration haut de gamme.\n\n"
            "Auriez-vous 15 minutes cette semaine pour en discuter ?"
        ),
    },
    'restauration': {
        'objets': [
            'PROPOSITION — Expérience digitale pour {entreprise}',
            'Suggestion — Une vitrine à la hauteur de {entreprise}',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "L'expérience {entreprise} commence bien avant l'arrivée — elle commence sur votre site. "
            "Un site qui ne donne pas envie coûte des couverts, même quand le restaurant est excellent.\n\n"
            "Un site repensé sur mesure peut renforcer votre image et transformer chaque visite en ligne en une décision de réservation.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des vitrines digitales "
            "pour les restaurants qui veulent que leur présence en ligne soit aussi soignée que leur cuisine.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de présence digitale. Pourtant, avant de pousser votre porte, vos clients cherchent "
            "en ligne — et sans site, vous n'existez pas dans leur décision.\n\n"
            "Un site sur mesure peut changer ça rapidement : images, menu, réservation, ambiance — tout ce qui donne envie avant l'arrivée.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow, "
            "je conçois des sites pour les établissements de restauration qui veulent une vitrine à leur image.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
    },
    'luxe': {
        'objets': [
            'PROPOSITION — Expérience digitale sur mesure · {entreprise}',
            'Suggestion — Une vitrine à la hauteur de l\'univers {entreprise}',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "L'univers de {entreprise} est soigné — mais votre site actuel ne reflète pas encore ce niveau d'exigence. "
            "Dans le luxe, un site générique décrédibilise une marque premium avant même que le client ait vu vos produits.\n\n"
            "Un site conçu sur mesure peut incarner le même niveau d'exigence que votre marque — et renforcer votre "
            "positionnement à chaque visite.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des expériences digitales "
            "pour les marques qui refusent le générique : design unique, animations fluides, aucun compromis esthétique.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de vitrine digitale — dans le luxe, cette absence parle avant même votre premier contact. "
            "Vos clients attendent la même exigence partout, y compris en ligne.\n\n"
            "Un site sur mesure peut incarner l'univers de votre marque et installer la désirabilité dès le premier regard.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow, "
            "je conçois des expériences digitales pour les marques premium qui refusent le compromis esthétique.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine ?"
        ),
    },
    'conseil': {
        'objets': [
            'PROPOSITION — Site web sur mesure · {entreprise}',
            'Suggestion — Aligner la présence digitale de {entreprise} avec votre niveau d\'expertise',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "{entreprise} a un positionnement fort — mais votre présence digitale ne reflète pas encore ce niveau. "
            "C'est souvent là que se font les premières impressions de vos prospects les plus qualifiés, avant même le premier échange.\n\n"
            "Un site à la hauteur de votre expertise peut qualifier vos prospects avant le premier rendez-vous — "
            "et justifier vos honoraires dès le premier regard.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des sites Webflow sur mesure "
            "pour les cabinets qui veulent que leur image digitale soit à la hauteur de leur expertise réelle.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de site professionnel. Pourtant, avant chaque premier rendez-vous, "
            "vos prospects vous googler — et une absence digitale fragilise la crédibilité avant même l'échange.\n\n"
            "Un site bien conçu peut devenir votre premier vendeur : il pose votre expertise, installe la confiance, "
            "et qualifie vos prospects en amont.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow, "
            "je conçois des sites pour les cabinets de conseil qui veulent une présence digitale à la hauteur de leur valeur.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
    },
    'liberal': {
        'objets': [
            'PROPOSITION — Site sur mesure · {entreprise}',
            'Suggestion — Une présence digitale à la hauteur de votre réputation',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "Dans votre secteur, la confiance est tout — et elle se forge en ligne bien avant le premier rendez-vous. "
            "Votre site actuel transmet-il vraiment le niveau d'expertise et de sérieux que vous incarnez ?\n\n"
            "Un site soigné et cohérent peut installer cette confiance dès le premier regard — "
            "et filtrer naturellement vers les clients qui correspondent vraiment à votre niveau.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des sites sur mesure "
            "pour les professionnels qui veulent que leur présence digitale soit digne de leur réputation.\n\n"
            "Auriez-vous 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de présence digitale. Or, avant de vous appeler, vos clients potentiels cherchent en ligne "
            "des signaux de confiance et de sérieux — et une absence de site est déjà un signal négatif.\n\n"
            "Un site professionnel conçu sur mesure peut devenir votre vitrine de crédibilité, disponible 24h/24.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, "
            "je conçois des sites pour les professions libérales qui veulent une présence digitale à leur image.\n\n"
            "Auriez-vous 15 minutes cette semaine pour en discuter ?"
        ),
    },
    'ecommerce': {
        'objets': [
            'PROPOSITION — Refonte du site {entreprise}',
            'Suggestion — Mettre le site de {entreprise} au niveau de vos produits',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "{entreprise} a de bons produits — mais votre site actuel ne leur rend pas justice. "
            "Le design ne reflète pas encore la valeur réelle de ce que vous proposez, "
            "et cela se ressent sur la perception client avant même l'achat.\n\n"
            "Un site repensé sur mesure peut élever la valeur perçue de vos produits "
            "et transformer chaque visite en une expérience qui donne envie d'acheter.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des expériences "
            "e-commerce premium pour les marques qui veulent que leur site soit aussi bon que leurs produits.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de présence e-commerce digne de ses produits. "
            "Dans un marché saturé, l'expérience en ligne est souvent ce qui fait la différence entre une vente et un abandon.\n\n"
            "Un site conçu sur mesure peut devenir votre meilleur commercial : il valorise vos produits, "
            "installe la confiance et convertit les visiteurs en acheteurs.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow, "
            "je conçois des expériences e-commerce pour les marques qui refusent le template générique.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine ?"
        ),
    },
    'formation': {
        'objets': [
            'PROPOSITION — Site sur mesure · {entreprise}',
            'Suggestion — Repositionner la présence digitale de {entreprise}',
        ],
        'corps_site': (
            "{prenom},\n\n"
            "L'autorité de {entreprise} se construit en ligne avant même le premier contact. "
            "Un site professionnel et bien conçu renforce la légitimité et justifie des tarifs à la hauteur de votre expertise.\n\n"
            "Si votre site actuel ne reflète pas encore ce positionnement, vous laissez de la valeur perçue sur la table.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — je conçois des sites Webflow sur mesure "
            "pour les formateurs et coaches qui veulent que leur présence digitale valide leur expertise.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
        'corps_nosite': (
            "{prenom},\n\n"
            "{entreprise} n'a pas encore de site professionnel. Or, pour un formateur ou coach, "
            "le site est le premier signal de crédibilité — avant LinkedIn, avant le bouche-à-oreille.\n\n"
            "Un site sur mesure peut devenir votre vitrine d'autorité : il pose votre expertise, "
            "rassure vos prospects et justifie vos tarifs avant le premier échange.\n\n"
            "Je me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, "
            "je conçois des sites pour les professionnels de la formation et du coaching premium.\n\n"
            "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
        ),
    },
}

def generate_email(lead, template_key, has_website):
    tpl = EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES['conseil'])
    prenom    = lead.get('prenom', 'Madame/Monsieur')
    entreprise = lead.get('entreprise', '')

    objet_tpl = tpl['objets'][hash(entreprise) % len(tpl['objets'])]
    objet = objet_tpl.format(entreprise=entreprise)

    corps_tpl = tpl['corps_site'] if has_website else tpl['corps_nosite']
    corps = corps_tpl.format(prenom=prenom, entreprise=entreprise)

    nb_mots = len(corps.split())
    return objet, corps, nb_mots

# ─── Add to Google Sheets ─────────────────────────────────────────────────────
def add_to_sheet(lead, token):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
           f'{SHEET_NAME}!A1:append?valueInputOption=USER_ENTERED')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    row = [
        lead['id_lead'],           # A
        lead['date_sourcing'],     # B
        lead['prenom'],            # C
        lead['nom'],               # D
        lead['poste'],             # E
        lead['email'],             # F
        lead['linkedin_url'],      # G
        lead['entreprise'],        # H
        lead['secteur'],           # I
        lead['taille_entreprise'], # J
        lead['ca_estime'],         # K
        lead['anciennete'],        # L
        lead['pays'],              # M
        lead['ville'],             # N
        lead['site_web'],          # O
        lead['score_icp'],         # P
        lead['statut_icp'],        # Q
        lead['qualite_site'],      # R
        lead['signal_besoin'],     # S
        'Nouveau',                 # T statut_lead
        '', '', '',                # U V W (date_premier_contact, objet, corps — remplis après)
        '',                        # X id_message_brevo
        '', '',                    # Y Z (ouverture — désactivé)
        '', '',                    # AA AB (réponse)
        '', '',                    # AC AD (relances)
        '',                        # AE notes
        'Envoyer email',           # AF prochaine_action
        TODAY,                     # AG date_prochaine_action
        '', '',                    # AH AI corps relances
        '',                        # AJ compte_envoi
    ]
    body = {'values': [row]}
    r = requests.post(url, json=body, headers=headers)
    return r.status_code in (200, 201)

def update_email_in_sheet(row_num, objet, corps, token):
    # PUT colonnes V:W
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'
           f'{SHEET_NAME}!V{row_num}:W{row_num}?valueInputOption=USER_ENTERED')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = {'values': [[objet, corps]]}
    requests.put(url, json=body, headers=headers)

def get_row_number(lead_id, token):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{SHEET_NAME}!A:A'
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    ids = [v[0] if v else '' for v in r.json().get('values', [])]
    try:
        return ids.index(lead_id) + 1  # 1-indexed
    except ValueError:
        return None

# ─── Main pipeline ────────────────────────────────────────────────────────────
def run():
    print('='*60)
    print(f'PIPELINE SOURCING — Objectif : {TARGET} leads')
    print(f'Date : {TODAY}')
    print('='*60)

    token = get_token()
    print('✅ Token GSheets obtenu')

    existing_companies, last_id = read_existing(token)
    print(f'✅ {len(existing_companies)} entreprises existantes chargées (dernier ID: LEAD-{last_id})')

    id_counter  = last_id + 1
    confirmed   = 0
    credits_used = 0
    rejected     = 0
    dupes        = 0
    results      = []

    for tag_id, sector_name, sector_score, template_key in SECTORS:
        if confirmed >= TARGET:
            break
        print(f'\n──── Secteur : {sector_name} ────')
        page = 1

        while confirmed < TARGET:
            print(f'  Page {page}...')
            people = apollo_search(tag_id, page=page)
            if not people:
                print(f'  → Plus de résultats pour ce secteur')
                break

            for person in people:
                if confirmed >= TARGET:
                    break

                company_name = ''
                org = person.get('organization') or {}
                company_name = (org.get('name') or '').strip()

                # Deduplicate
                if company_name.lower() in existing_companies:
                    dupes += 1
                    continue
                if not company_name:
                    continue

                # Reveal email (1 crédit)
                apollo_id = person.get('id')
                if not apollo_id:
                    continue

                revealed = reveal_contact(apollo_id)
                credits_used += 1
                if not revealed:
                    rejected += 1
                    continue

                email = (revealed.get('email') or '').strip()
                if not email:
                    rejected += 1
                    continue

                # Full ICP score
                score, statut, detail = score_icp(revealed, sector_score)
                if score < ICP_MIN:
                    rejected += 1
                    continue

                # Build lead
                r_org   = (revealed.get('organization') or {})
                prenom  = (revealed.get('first_name') or '').strip()
                nom     = (revealed.get('last_name') or '').strip()
                poste   = (revealed.get('title') or '').strip()
                linkedin = (revealed.get('linkedin_url') or '').strip()
                ville   = (revealed.get('city') or '').strip()
                pays    = (revealed.get('country') or 'France').strip()
                site    = (r_org.get('website_url') or '').strip()
                taille  = r_org.get('estimated_num_employees', '') or ''
                ca      = r_org.get('annual_revenue', '') or ''
                founded = r_org.get('founded_year', '') or ''
                anciennete = f'{2026 - int(founded)} ans' if founded else ''
                ca_str = str(int(ca)) if ca else ''

                lead_id = f'LEAD-{id_counter}'
                id_counter += 1

                has_website = bool(site)
                qualite_site = 'inexistant' if not site else 'basique'
                signal_besoin = 'Site web inexistant' if not site else 'Site web basique / potentiel de refonte'

                objet, corps, nb_mots = generate_email(
                    {'prenom': prenom or 'Madame/Monsieur', 'entreprise': company_name},
                    template_key, has_website
                )

                lead = {
                    'id_lead':          lead_id,
                    'date_sourcing':    TODAY,
                    'prenom':           prenom,
                    'nom':              nom,
                    'poste':            poste,
                    'email':            email,
                    'linkedin_url':     linkedin,
                    'entreprise':       company_name,
                    'secteur':          sector_name,
                    'taille_entreprise': str(taille),
                    'ca_estime':        ca_str,
                    'anciennete':       anciennete,
                    'pays':             pays,
                    'ville':            ville,
                    'site_web':         site,
                    'score_icp':        str(score),
                    'statut_icp':       statut,
                    'qualite_site':     qualite_site,
                    'signal_besoin':    signal_besoin,
                    'objet_email':      objet,
                    'corps_email':      corps,
                }

                # Add to GSheets
                ok = add_to_sheet(lead, token)
                if ok:
                    existing_companies.add(company_name.lower())
                    confirmed += 1
                    results.append(lead)
                    print(f'  ✅ [{confirmed:3d}/{TARGET}] {lead_id} — {company_name} ({sector_name}) — Score: {score} ({statut})')

                    # Update email columns (V:W)
                    row_num = get_row_number(lead_id, token)
                    if row_num:
                        update_email_in_sheet(row_num, objet, corps, token)

                    time.sleep(0.5)  # éviter le rate limit

                else:
                    print(f'  ❌ Erreur écriture sheet pour {company_name}')

            page += 1
            time.sleep(1)

    # ─── Rapport final ────────────────────────────────────────────────────────
    print('\n' + '='*60)
    print(f'RAPPORT FINAL — {TODAY}')
    print('='*60)
    print(f'✅ Leads confirmés    : {confirmed}')
    print(f'💳 Crédits Apollo utilisés : {credits_used}')
    print(f'❌ Leads rejetés (score < {ICP_MIN}) : {rejected}')
    print(f'🔁 Doublons ignorés   : {dupes}')
    print()
    print(f'{"ID":<12} {"Entreprise":<35} {"Secteur":<22} {"Score":>5} {"Statut"}')
    print('-'*90)
    for lead in results:
        print(f'{lead["id_lead"]:<12} {lead["entreprise"][:34]:<35} {lead["secteur"][:21]:<22} {lead["score_icp"]:>5} {lead["statut_icp"]}')

    return confirmed, credits_used

if __name__ == '__main__':
    run()

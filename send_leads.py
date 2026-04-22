#!/usr/bin/env python3
"""Script principal pour envoyer tous les emails de prospection."""
import json
import time
import requests
import jwt
import urllib.parse

# Configuration
BREVO_KEY = "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"
SPREADSHEET_ID = "1ldw_jOzP6C2t5GAijORNAOKI6wqWnSkwQbph3YyAKBM"
SENDER_NAME = "Ajdaini Studio"
SENDER_EMAIL = "contact@ajdaini.studio"
BASE_DATE = "2026-04-10"
SIGNATURE = "\n\n--\nAjdaini Studio\nExpert Webflow - Web Designer\nhttps://ajdaini.studio"

# Données des leads (row, prenom, nom, email)
LEADS = [
    (185, "Mehmet", "Akdemir", "me.akdemir@placepizza.fr"),
    (186, "Laurent", "Beyron", "laurent.beyron@villesetpaysages.fr"),
    (187, "Vincent", "Fournier", "vf@oxgen.fr"),
    (188, "Richard", "Teuscher", "rteuscher@capteo.com"),
    (189, "Fabrice", "Aubergier", "f.aubergier@chocolats-bellanger.com"),
    (190, "Alexis", "Guillard", "aguillard@detconsultants.com"),
    (191, "Nicolas", "Miravette", "nicolas.miravette@makinov.fr"),
    (192, "Raffi", "Kizilian", "raffi.kizilian@ireo.fr"),
    (193, "Arnaud", "Eymery", "arnaud.eymery@degest.com"),
    (194, "Joackim", "Noblot", "j.noblot@hfpc.fr"),
    (195, "Yann", "Debruyne", "y.debruyne@variance-ingenierie.fr"),
    (196, "Mylene", "Vermorel", "mylene@chateaudecourban.com"),
    (197, "Orlando", "Gaudron", "o.gaudron@hicoquelles.com"),
    (198, "Laurent", "Seven", "laurent.seven@dcb-logistics.com"),
    (199, "Antoine", "Rizzo", "a.rizzo@arcentreprise.com"),
    (200, "Julien", "Benamout", "jbenamout@pulsim.fr"),
    (201, "Jacques", "Goubin", "jgoubin@jouinmanku.com"),
    (202, "Marc", "Poulpiquet", "marc@crowe.com"),
    (203, "Benjamin", "Vilain", "benjamin.vilain@baldwin-partners.com"),
    (204, "Yohan", "Saules", "yohan.saules@infinitif.com"),
    (205, "Dominique", "Richard", "drichard@cerenn.com"),
    (206, "David", "Miet", "david.miet@vivantes.fr"),
    (207, "Nathalie", "Vaillant", "nathalie@teresamonroe.com"),
    (208, "Jeoffrey", "Rambinintsoa", "jeoffrey.rambinintsoa@pyxis-support.com"),
    (209, "Pierre", "Etchanchu", "pierre.etchanchu@wizin.fr"),
]

# Contenus déjà lus (sujet, corps) dans l'ordre des rows 185-209
CONTENTS = [
    (
        "Suggestion — La présence digitale de Place Pizza à la hauteur de votre établissement",
        "Monsieur Akdemir,\n\nDans un marché de la pizza en France où les enseignes leaders investissent massivement dans leur présence digitale, l'expérience commence avant l'arrivée — et un site qui se fond dans la masse ne suffit plus à convaincre. Place Pizza a bâti une vraie identité, mais sa vitrine digitale ne reflète pas encore pleinement la cohérence entre l'établissement et ce que vos clients trouvent en ligne.\n\nUn site sur mesure, pensé pour donner envie avant même de franchir la porte, transforme chaque visiteur en client potentiel.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans la création de sites web qui valorisent l'identité des enseignes de restauration et renforcent leur attractivité digitale.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Vos projets méritent une vitrine à leur niveau",
        "Laurent,\n\nVotre atelier livre des projets d'aménagement urbain complexes pour des collectivités exigeantes — mais le site actuel, construit sur Elementor avec des plugins standard, ne rend pas justice à la qualité de ces réalisations. Pour un maître d'ouvrage qui vous évalue avant toute réunion, l'écart est immédiatement perceptible.\n\nUn portfolio premium sur mesure transforme cette première impression en crédibilité instantanée, et positionne Villes & Paysages au niveau des projets que vous signez.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow premium pour les cabinets d'architecture et d'urbanisme.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Vos prospects DSI vous jugent avant de vous rencontrer",
        "Victor,\n\nOxGEN adresse les DSI de grands groupes sur des sujets stratégiques — c'est une niche à forte valeur. Pourtant, le site actuel repose sur Elementor et des composants WordPress standard qui ne reflètent pas ce positionnement d'expert premium. Un DSI qui arrive sur votre site se forgera une opinion en 8 secondes.\n\nUn site sur mesure, pensé pour ce niveau d'interlocuteur, justifie vos honoraires dès le premier regard et renforce chaque prise de contact.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil B2B à positionnement expert.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Capteo mérite mieux que son site actuel",
        "Romain,\n\nCapteo a réalisé plus de 400 missions pour les plus grandes banques européennes — mais le site trahit une esthétique 2018, avec des patterns WordPress standards et un tracking encore en codes UA. Pour un prospect qui arrive froid, l'écart avec le niveau de vos clients est visible.\n\nUn site repensé de zéro pose Capteo comme le cabinet de référence que vous êtes, avant même le premier échange.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil en transformation financière.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Vos chocolats méritent un site à la hauteur",
        "Frédéric,\n\nLa Chocolaterie Bellanger propose des créations artisanales haut de gamme — mais le site actuel, monté sur WooCommerce avec des plugins standard, offre une expérience bien en dessous de la valeur perçue de vos produits. Un acheteur en ligne juge la qualité de l'artisan à travers celle du site.\n\nUn site sur mesure renforce la valeur perçue de chaque collection et transforme la visite en ligne en prolongement naturel de l'expérience boutique.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow premium pour les maisons artisanales et le retail haut de gamme.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "30 ans d'expertise méritent un site distinctif",
        "Amaury,\n\nD&Consultants accompagne des projets d'innovation depuis plus de 30 ans — une légitimité rare. Mais le site repose sur le thème WordPress DT The7, identifiable par tout consultant tech, ce qui dilue cette singularité dès la première visite. Vos prospects vous jugent avant de vous rencontrer, et un template envoie un signal inverse à votre positionnement.\n\nUn site entièrement sur mesure pose votre expertise comme premier vecteur de crédibilité.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil en innovation B2B.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Votre site Webflow peut aller plus loin",
        "Nicolas,\n\nMakin'Ov a déjà investi dans un site Webflow avec GSAP — c'est une bonne base. Mais pour un cabinet qui accompagne EDF, Orange ou AXA sur leur vision à 10 ans, le niveau d'exécution visuelle actuelle laisse encore de la marge : animations sous-exploitées, architecture de contenu perfectible, impact premium pas encore au rendez-vous.\n\nUn site à ce niveau de maîtrise Webflow renforce directement la perception d'un cabinet qui pense différemment.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, spécialisé dans les sites pour cabinets de conseil et de prospective.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Votre site filtre-t-il vers la clientèle que vous visez ?",
        "Raffi,\n\nIREO conseille et pilote des projets immobiliers d'envergure — mais le site actuel, construit sur Kadence avec des éléments WordPress standards, n'incite pas un investisseur ou un maître d'ouvrage à franchir immédiatement le pas. Dans l'immobilier, l'acheteur visite le site avant de visiter le bien, et évalue le sérieux du partenaire au même moment.\n\nUn site premium filtre naturellement vers une clientèle qualifiée et légitime des honoraires de conseil au plus haut niveau.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les acteurs du conseil immobilier.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "La confiance de vos clients se forge aussi en ligne",
        "Arnaud,\n\nDEGEST intervient sur des sujets sensibles — expertise CSE, santé-sécurité au travail — où la confiance est la première raison de vous mandater. Pourtant, le site actuel repose sur Elementor avec une architecture classique WordPress qui ne se distingue pas des dizaines de cabinets concurrents sur le marché.\n\nUn site sur mesure transforme cette confiance en signal visible dès la première recherche Google, avant tout appel.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow pour les cabinets de conseil et d'expertise auprès des instances représentatives.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "François Premier Hospitality sans site propre en 2026",
        "Julien,\n\nFrançois Premier Hospitality gère des établissements 4 étoiles dans Paris — mais le groupe n'a pas de site web propre identifiable. En 2026, 80 % des clients visitent le site avant de réserver : sans vitrine digitale maîtrisée, vous êtes entièrement dépendant des OTAs et plateformes tierces, qui captent la marge et la relation client.\n\nL'expérience commence avant l'arrivée — et c'est votre site qui donne le premier service.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow premium pour les groupes hôteliers indépendants.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Variance Ingénierie mérite mieux que Mobirise",
        "Yves,\n\nLe Groupe Variance Ingénierie cumule plus de 40 ans d'expertise et 95 collaborateurs — mais le site actuel est construit sur Mobirise, un builder low-cost dont la signature reste visible dans le code. Pour un maître d'ouvrage qui vous compare à d'autres bureaux d'études, ce détail suffit à créer le doute sur votre niveau d'exigence.\n\nVos réalisations méritent une vitrine à leur niveau, capable de servir de premier argument de crédibilité auprès de donneurs d'ordre institutionnels.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les bureaux d'études et groupes d'ingénierie.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "L'étoile Michelin mérite un site à sa hauteur",
        "Mylene,\n\nLe Château de Courban réunit 4 étoiles, une étoile Michelin et un Spa Nuxe de 300 m² — un positionnement de luxe authentique. Pourtant, le site actuel ne restitue pas cette expérience sensorielle avant l'arrivée : le design manque de la sophistication attendue par une clientèle qui compare avec des maisons Relais & Châteaux.\n\nL'expérience commence avant l'arrivée — un site premium, c'est le premier service rendu à vos clients.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les établissements hôteliers et gastronomiques de prestige.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Votre site est inaccessible — vos réservations en pâtissent",
        "Olivier,\n\nHicoquelles.com est actuellement inaccessible pour cause de certificat SSL invalide — concrètement, tout visiteur reçoit un avertissement de sécurité de son navigateur et repart immédiatement. Pour un Holiday Inn 4 étoiles avec 118 chambres, un spa et 6 salles de réunion, chaque jour sans site fonctionnel représente des réservations directes perdues au profit des OTAs.\n\nL'expérience commence avant l'arrivée — votre site doit être le premier service rendu, pas un obstacle.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow performants pour les établissements hôteliers.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "DCB Logistics : 200 000 m² sans site accessible",
        "Laurent,\n\nDCB Logistics développe près de 200 000 m² de plateformes logistiques — mais dcb-logistics.com est actuellement inaccessible à cause d'un certificat SSL invalide. Pour des investisseurs ou partenaires institutionnels qui cherchent à vous qualifier en amont d'une réunion, l'absence de site fonctionnel est un signal rédhibitoire.\n\nDans l'immobilier logistique, votre site filtre naturellement vers une clientèle qualifiée — à condition qu'il existe et soit à la hauteur des projets que vous portez.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les acteurs de l'immobilier professionnel.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Groupe RIZZO : pas de vitrine pour votre activité parisienne",
        "Antoine,\n\nArcentreprise.com redirige vers le site du Groupe Rizzo, focalisé sur la région lémanique — ce qui signifie que votre activité parisienne n'a aucune vitrine digitale propre. Un prospect ou partenaire parisien qui cherche à vous qualifier en ligne repart sans trouver ce qu'il cherche.\n\nDans l'immobilier, l'acheteur visite le site avant le bien — et un site dédié, ancré dans le marché parisien, filtre naturellement vers la clientèle que vous visez.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow premium pour les promoteurs et acteurs de l'immobilier.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "1,5 milliard de projets, un site qui ne le reflète pas",
        "Julien,\n\nPulsim affiche plus de 100 opérations immobilières pour 1,5 milliard d'euros de projets — des chiffres qui imposent le respect. Mais le site actuel, construit sur WordPress avec un design standard, ne communique pas ce track record avec la gravité et la sophistication qu'un co-investisseur ou family office attend avant de prendre contact.\n\nDans l'immobilier, votre site filtre naturellement vers une clientèle qualifiée — à condition qu'il soit à la hauteur de vos réalisations.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les acteurs du capital immobilier.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Jouin Manku mérite une vitrine aussi exceptionnelle que ses projets",
        "J.,\n\nJouin Manku livre des intérieurs pour Park Hyatt Tokyo et Van Cleef & Arpels — des projets d'une rareté absolue. Pourtant, le site repose sur des technologies conventionnelles, sans animations ni interactions à la mesure de cette excellence. Pour un client international qui découvre le studio en ligne, le contraste entre la qualité des réalisations et l'expérience digitale est perceptible.\n\nVos réalisations méritent une vitrine à leur niveau, avec des animations qui donnent à ressentir avant même la réunion.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, spécialisé GSAP pour les studios de design et d'architecture de prestige.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Crowe Praxiam : invisible en ligne hors du réseau global",
        "Marc,\n\nCrowe Praxiam fait partie du 8e réseau mondial d'audit et conseil — mais en dehors de crowe.com, l'entité n'a pas de site propre. Un prospect qui cherche spécifiquement votre expertise France tombe sur une page réseau globale, sans l'identité, l'équipe et les références qui justifient de vous appeler plutôt qu'un autre cabinet.\n\nVos prospects vous jugent avant de vous rencontrer — un site dédié est le premier vecteur de crédibilité pour votre positionnement parisien.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil et d'audit à positionnement expert.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Un cabinet Industrie 4.0 ne devrait pas avoir un site 1.0",
        "Benjamin,\n\nBaldwin Partners conseille Safran, Thales et ENGIE sur l'Industrie 4.0 — un positionnement de pointe. Mais le site actuel est construit sur des templates Elementor standards, à l'opposé de l'image d'expert en transformation digitale industrielle que vous portez. Pour un prospect qui vous évalue avant un appel d'offres, le signal est contre-productif.\n\nVos prospects vous jugent avant de vous rencontrer — un site sur mesure justifie vos honoraires dès le premier regard.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil en ingénierie et transformation industrielle.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Infinitif : une tagline ne fait pas un site",
        "Yohan,\n\nInfinitif a été lancé officiellement en 2024 avec une promesse forte — mais le site actuel se limite à une tagline. Pour convaincre des décideurs en banque, assurance ou mutuelle de vous confier une mission de transformation, votre site est le premier vecteur de crédibilité qu'ils consultent avant de décrocher leur téléphone.\n\nLa confiance se forge en ligne — et votre expertise mérite d'être visible avec la même exigence que vos missions.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets de conseil en transformation organisationnelle.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Vos espaces sont premium — votre site devrait l'être aussi",
        "David,\n\nCerenn conçoit des espaces de travail modulaires haut de gamme avec une identité visuelle forte — mais le site repose sur le builder Tatsu, ce qui plafonne la qualité d'exécution perçue. Pour un acheteur B2B qui commande des aménagements à plusieurs dizaines de milliers d'euros, l'expérience utilisateur du site influence directement la valeur perçue des produits.\n\nUn site sur mesure, à la hauteur de vos réalisations, devient lui-même un argument de vente.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow premium pour les marques de design et d'aménagement d'espaces.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Villes Vivantes innove — son site devrait l'exprimer",
        "David,\n\nVilles Vivantes a développé quatre technologies d'urbanisme inédites et collabore avec la Caisse des Dépôts — c'est un positionnement d'innovateur rare. Pourtant, le site actuel repose sur WordPress avec un design standard, qui ne traduit pas cette singularité auprès des collectivités et investisseurs institutionnels que vous ciblez.\n\nVos réalisations méritent une vitrine à leur niveau — un portfolio premium génère une crédibilité instantanée auprès des maîtres d'ouvrage.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les acteurs de l'urbanisme et de l'innovation territoriale.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "Teresa Monroe : la data mérite un site qui la met en scène",
        "Nathalie,\n\nTeresa Monroe est déjà sur Webflow — bonne base. Mais pour un cabinet certifié B Corp qui vend de l'expérience client et de la data analytics à Michelin et Leroy Merlin, le design actuel reste dans les codes du conseil standard. L'identité visuelle ne reflète pas encore la singularité que vous revendiquez face à vos concurrents.\n\nVos prospects vous jugent avant de vous rencontrer — un site qui incarne votre approche différenciante justifie vos honoraires dès le premier regard.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié, spécialisé dans les sites pour les cabinets de conseil à positionnement différenciant.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "80 clients institutionnels méritent un site institutionnel",
        "Jeoffrey,\n\nPyxis Support affiche plus de 80 références — RATP, SNCF, ministères — et développe des solutions IA pour la commande publique. Pourtant, le site repose sur le thème WordPress Mesmerize, un template commercial reconnaissable, qui crée un décalage avec la stature de vos clients et la technicité de vos solutions.\n\nVos prospects vous jugent avant de vous rencontrer — la confiance se forge en ligne, et votre expertise mérite d'être visible avec le même niveau d'exigence.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — spécialisé dans les sites Webflow sur mesure pour les cabinets d'AMO et de conseil en transformation publique.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
    (
        "WIZIN : un beau site, mais Webflow l'emmènerait plus loin",
        "Pierre,\n\nWIZIN a déjà un site soigné avec animations et une vraie identité visuelle — vous avez compris que le digital est un levier de crédibilité. Mais le site repose sur WordPress/Bricks, avec les limitations techniques que cela implique. Dans un marché de consultants indépendants très concurrentiel, l'écart entre un site WordPress animé et un site Webflow sur mesure se ressent sur la conversion.\n\nVos prospects vous jugent avant de vous rencontrer — passer à Webflow natif avec des interactions maîtrisées renforcerait votre avance.\n\nJe me présente, je suis Ilyass, à la tête du studio ajdaini.studio — expert Webflow certifié spécialisé dans les plateformes pour collectifs de consultants.\n\nSeriez-vous disponible 15 minutes cette semaine pour en discuter ?"
    ),
]


def get_token():
    key = json.load(open('/Users/ilyass/Desktop/agents/marketing-team/prospection-team/credentials/gsheets_key.json'))
    now = int(time.time())
    claim = {
        'iss': key['client_email'],
        'scope': 'https://www.googleapis.com/auth/spreadsheets',
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': now,
        'exp': now + 3600
    }
    signed = jwt.encode(claim, key['private_key'], algorithm='RS256')
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': signed
    })
    return r.json()['access_token']


def lock_row(token, row):
    requests.put(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/leads_tracker!T{row}?valueInputOption=USER_ENTERED',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'values': [['En cours d\'envoi']]}
    )


def update_row_success(token, row, scheduled, subject, body, message_id):
    r = requests.put(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/leads_tracker!T{row}:X{row}?valueInputOption=USER_ENTERED',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'values': [['Email envoyé', scheduled, subject, body, message_id]]}
    )
    return r.status_code


def update_row_status(token, row, status):
    requests.put(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/leads_tracker!T{row}?valueInputOption=USER_ENTERED',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'values': [[status]]}
    )


def calc_scheduled_at(index):
    """Calcule le scheduledAt basé sur l'index d'envoi (0 = premier envoi)."""
    base_hour = 9
    base_min = 0
    total_minutes = base_min + (index * 3)
    hour = base_hour + total_minutes // 60
    minute = total_minutes % 60
    return f"2026-04-10T{hour:02d}:{minute:02d}:00+02:00"


def send_email(email, name, subject, body, scheduled_at):
    text_content = body + SIGNATURE
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": email, "name": name}],
        "subject": subject,
        "textContent": text_content,
        "scheduledAt": scheduled_at
    }
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"Content-Type": "application/json", "api-key": BREVO_KEY},
        json=payload
    )
    return r.status_code, r.json()


def main():
    token = get_token()
    emails_sent = 0
    results = []

    # LEAD-233 (row 185) a déjà été envoyé avec messageId <202604100325.18549940884@smtp-relay.mailin.fr>
    # On doit mettre à jour son sheet et continuer à partir de LEAD-234
    print("=== Mise à jour sheet LEAD-233 (déjà envoyé) ===")
    row_233 = 185
    subject_233 = CONTENTS[0][0]
    body_233 = CONTENTS[0][1]
    scheduled_233 = calc_scheduled_at(0)
    message_id_233 = "<202604100325.18549940884@smtp-relay.mailin.fr>"
    status = update_row_success(token, row_233, scheduled_233, subject_233, body_233, message_id_233)
    print(f"LEAD-233 sheet update: HTTP {status}")
    emails_sent = 1
    results.append({
        'lead_id': 'LEAD-233',
        'row': row_233,
        'email': 'me.akdemir@placepizza.fr',
        'status': 'Envoyé',
        'scheduled_at': scheduled_233,
        'message_id': message_id_233
    })

    # Traitement des leads 234-257 (index 1 à 24)
    for i in range(1, 25):
        row, prenom, nom, email = LEADS[i]
        subject, body = CONTENTS[i]
        lead_id = f"LEAD-{233 + i}"

        print(f"\n=== {lead_id} - {prenom} {nom} ({email}) ===")

        # Étape 5 : Verrouillage
        lock_row(token, row)
        print(f"  Verrouillage col T row {row} OK")

        # Étape 6 : Calcul scheduledAt
        scheduled_at = calc_scheduled_at(emails_sent)
        print(f"  scheduledAt = {scheduled_at} (index {emails_sent})")

        # Étape 7 : Envoi
        full_name = f"{prenom} {nom}"
        http_code, resp = send_email(email, full_name, subject, body, scheduled_at)
        print(f"  Brevo response: HTTP {http_code} - {resp}")

        if http_code in [200, 201, 202]:
            message_id = resp.get('messageId', '')
            # Étape 8 : MAJ sheet
            sheet_status = update_row_success(token, row, scheduled_at, subject, body, message_id)
            print(f"  Sheet updated: HTTP {sheet_status}")
            emails_sent += 1
            results.append({
                'lead_id': lead_id,
                'row': row,
                'email': email,
                'status': 'Envoyé',
                'scheduled_at': scheduled_at,
                'message_id': message_id
            })
        elif http_code >= 500:
            print(f"  Erreur 5xx, retry dans 60s...")
            time.sleep(60)
            http_code2, resp2 = send_email(email, full_name, subject, body, scheduled_at)
            if http_code2 in [200, 201, 202]:
                message_id = resp2.get('messageId', '')
                update_row_success(token, row, scheduled_at, subject, body, message_id)
                emails_sent += 1
                results.append({
                    'lead_id': lead_id,
                    'row': row,
                    'email': email,
                    'status': 'Envoyé',
                    'scheduled_at': scheduled_at,
                    'message_id': message_id
                })
            else:
                update_row_status(token, row, "Erreur envoi")
                results.append({
                    'lead_id': lead_id,
                    'row': row,
                    'email': email,
                    'status': 'Erreur envoi',
                    'scheduled_at': scheduled_at,
                    'message_id': ''
                })
        else:
            update_row_status(token, row, "Erreur envoi")
            results.append({
                'lead_id': lead_id,
                'row': row,
                'email': email,
                'status': 'Erreur envoi',
                'scheduled_at': scheduled_at,
                'message_id': ''
            })

    print("\n\n=== RÉSUMÉ FINAL ===")
    sent = [r for r in results if r['status'] == 'Envoyé']
    errors = [r for r in results if r['status'] == 'Erreur envoi']

    print(f"Emails envoyés : {len(sent)}")
    print(f"Emails échoués : {len(errors)}")

    print("\n--- Planning des envois ---")
    for r in sent:
        print(f"  {r['lead_id']} | {r['email']} | {r['scheduled_at']} | {r['message_id']}")

    if errors:
        print("\n--- Erreurs ---")
        for r in errors:
            print(f"  {r['lead_id']} | {r['email']} | {r['status']}")

    # Sauvegarder résultats JSON
    with open('/tmp/send_leads_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nRésultats sauvegardés dans /tmp/send_leads_results.json")


if __name__ == '__main__':
    main()

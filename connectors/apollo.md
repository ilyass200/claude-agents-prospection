# Connecteur Apollo.io

## Présentation

Apollo.io est la plateforme de sourcing B2B utilisée par l'Agent Sourcing. Ce fichier contient les instructions exactes et validées pour appeler l'API Apollo correctement.

---

## Configuration

```
BASE_URL : https://api.apollo.io/api/v1
CLE_API  : $APOLLO_API_KEY  ← définie dans prospection-team/.env
```

> Pour configurer ta clé API Apollo :
> 1. Connecte-toi sur https://app.apollo.io
> 2. Va dans Settings → Integrations → API
> 3. Copie ta clé API (40+ caractères)
> 4. Ouvre `prospection-team/.env` et remplace la valeur de `APOLLO_API_KEY`
> ⚠️ Après un upgrade de plan, régénère une nouvelle clé — l'ancienne reste sur l'ancien plan

---

## Pipeline en 2 étapes — OBLIGATOIRE

> ⚠️ Les résultats de recherche retournent les données **masquées** (nom, email, LinkedIn).
> Il faut obligatoirement faire une 2ème requête `people/match` par contact pour révéler les données.
> Chaque révélation d'email = **1 crédit Apollo**.

```
Étape 1 : mixed_people/api_search  → liste de contacts avec IDs (données masquées)
Étape 2 : people/match (par ID)    → données complètes révélées (email, nom, LinkedIn)
```

---

## Endpoint 1 — Recherche de prospects `POST /api/v1/mixed_people/api_search`

**⚠️ Ne pas utiliser `mixed_people/search` (déprécié) ni `contacts/search` (CRM uniquement)**

```json
POST https://api.apollo.io/api/v1/mixed_people/api_search
Headers:
  Content-Type: application/json
  X-Api-Key: $APOLLO_API_KEY

Body:
{
  "person_titles": [
    "CEO", "Founder", "Co-Founder", "PDG",
    "Directeur Général", "DG", "Gérant", "Président",
    "Directeur", "Fondateur", "Associé", "Managing Director"
  ],
  "person_locations": ["$PAYS_CIBLE"],
  "organization_num_employees_ranges": ["15,500"],
  "organization_industry_tag_ids": [
    → Lire la section "Filtres sectoriels validés" ci-dessous pour les tag IDs exacts à injecter ici
  ],
  "reveal_personal_emails": false,
  "reveal_phone_number": false,
  "page": 1,
  "per_page": 25
}
```

> ⚠️ Ne pas ajouter `revenue_range` dans le body — non supporté, cause une erreur silencieuse
> ⚠️ Utiliser **`organization_industry_tag_ids`** (liste d'IDs hexadécimaux) — validé et fonctionnel
> ⚠️ Ne pas utiliser `organization_industries` (strings) — retourne 0 résultats avec le nouveau endpoint
> ⚠️ Utiliser `person_locations` et NON `organization_locations` pour filtrer par pays

**Réponse — champs réellement disponibles (masqués) :**

> ⚠️ L'objet `organization` retourné par `api_search` est **minimaliste** — il ne contient que des flags booléens.
> Les champs `industry`, `annual_revenue`, `founded_year`, `website_url` ne sont PAS présents dans la réponse de recherche.
> Ces données complètes ne sont disponibles qu'après révélation via `people/match` (Endpoint 2).

```json
{
  "total_entries": 58963,
  "people": [
    {
      "id": "id_apollo_unique",
      "first_name": null,
      "last_name": null,
      "title": null,
      "email": null,
      "linkedin_url": null,
      "organization": {
        "name": "Nom Entreprise",
        "has_industry": true,
        "has_phone": true,
        "has_city": true,
        "has_state": true,
        "has_country": true,
        "has_zip_code": true,
        "has_revenue": false,
        "has_employee_count": true
      }
    }
  ]
}
```

> **Conséquence sur le scoring ICP :** puisque `industry`, `annual_revenue` et `founded_year` ne sont pas disponibles
> au stade de la recherche, le scoring doit s'appuyer sur :
> - **Secteur** : connu implicitement via le `organization_industry_tag_id` utilisé dans le filtre de recherche
> - **Budget** : proxy basé sur `has_employee_count` → si true, estimer selon la taille connue (10–15 = ~300k, 20–50 = ~750k, 50+ = ~2M)
> - **Ancienneté & Besoin** : scorer après révélation via `people/match`, qui retourne les champs complets

---

## Endpoint 2 — Révélation d'un contact `POST /api/v1/people/match`

Appeler cet endpoint pour chaque ID récupéré à l'étape 1. Coûte **1 crédit/contact**.

```json
POST https://api.apollo.io/api/v1/people/match
Headers:
  Content-Type: application/json
  X-Api-Key: $APOLLO_API_KEY

Body:
{
  "id": "id_apollo_unique",
  "reveal_personal_emails": false
}
```

**Réponse — champs complets révélés :**
```json
{
  "person": {
    "first_name": "Prénom",
    "last_name": "Nom",
    "title": "Poste",
    "email": "prenom.nom@entreprise.com",
    "linkedin_url": "https://linkedin.com/in/...",
    "city": "Paris",
    "country": "France",
    "organization": {
      "name": "Entreprise",
      "industry": "secteur",
      "estimated_num_employees": 50,
      "annual_revenue": 5000000,
      "founded_year": 2010,
      "website_url": "https://..."
    }
  }
}
```

> ⚠️ Appeler uniquement pour les leads ayant passé le scoring ICP (≥ $ICP_SCORE_MINIMUM)
> pour ne pas gaspiller de crédits sur des leads non qualifiés

---

## Endpoint 3 — Enrichissement d'une entreprise `POST /api/v1/organizations/enrich`

```json
POST https://api.apollo.io/api/v1/organizations/enrich
Headers:
  Content-Type: application/json
  X-Api-Key: $APOLLO_API_KEY

Body:
{
  "domain": "entreprise.com"
}
```

---

## Filtres sectoriels validés — `organization_industry_tag_ids`

> Utiliser les tag IDs ci-dessous dans le champ `organization_industry_tag_ids` de la recherche.
> Ces IDs ont été **testés et validés** sur l'API Apollo (`api_search`).
> Le secteur est ainsi connu implicitement depuis le filtre, sans besoin de lire le champ `organization.industry`.

| Secteur | Tag ID | Score ICP |
|---|---|---|
| Immobilier (`real estate`) | `5567cd477369645401010000` | 25 pts |
| Hôtellerie (`hospitality`) | `5567ce9d7369643bc19c0000` | 25 pts |
| Restauration (`restaurants`) | `5567e0e0736964198de70700` | 25 pts |
| Luxe & Bijouterie (`luxury goods & jewelry`) | `5567cda97369644cfd3e0000` | 25 pts |
| Conseil & Management (`management consulting`) | `5567cdd47369643dbf260000` | 20 pts |
| Expertise comptable (`accounting`) | `5567ce1f7369643b78570000` | 20 pts |
| Retail & Commerce (`retail`) | `5567ced173696450cb580000` | 20 pts |
| E-learning (`e-learning`) | `5567e19c7369641c48e70100` | 15 pts |
| Formation & Coaching (`professional training & coaching`) | `5567cd49736964541d010000` | 15 pts |

> Pour chercher dans **tous les secteurs cibles** en une seule requête, passer les 9 tag IDs ensemble.
> Pour cibler un secteur précis, passer un seul tag ID.
> Les secteurs `apparel & fashion`, `legal services`, `architecture & planning`, `business consulting`, `consumer goods`
> n'ont pas encore de tag ID validé — utiliser les 9 secteurs ci-dessus comme base.

---

## Gestion des crédits (plan Basic — 2 500 crédits/mois)

| Action | Coût | Stratégie |
|---|---|---|
| Recherche `mixed_people/api_search` | 0 crédit | Utiliser librement pour identifier |
| Révélation email `people/match` | 1 crédit | Uniquement après scoring ICP ≥ $ICP_SCORE_MINIMUM |
| Téléphone | 8 crédits | ❌ Ne pas utiliser |
| Enrich data Apollo | 1-8 crédits | ❌ Ne pas utiliser — Claude enrichit à la place |

**Règle d'or :** Rechercher → Scorer avec les données masquées → Révéler uniquement les qualifiés

---

## Codes d'erreur courants

| Code / Message | Cause | Action |
|---|---|---|
| `API_INACCESSIBLE` | Mauvais plan ou ancienne clé | Régénérer la clé après upgrade |
| `Invalid access credentials` | Clé invalide ou tronquée | Vérifier longueur clé (40+ chars) |
| `deprecated` dans le message | Endpoint obsolète | Utiliser `mixed_people/api_search` |
| `API key must be passed in the X-Api-Key header` | Clé passée en body ou query param | Passer la clé dans le header `X-Api-Key` uniquement |
| 0 résultats avec `organization_industries` | Paramètre string non supporté par le nouveau endpoint | Remplacer par `organization_industry_tag_ids` (voir table ci-dessus) |
| 429 | Rate limit | Attendre 60 secondes, réessayer |

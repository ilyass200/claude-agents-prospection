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
    "CEO", "Founder", "Co-Founder",
    "Directeur Général", "Dirigeant",
    "Directeur Marketing", "CMO",
    "Responsable Communication"
  ],
  "organization_locations": ["$PAYS_CIBLE"],
  "organization_num_employees_ranges": ["10,500"],
  "organization_industries": [
    → Lire context.md → SECTION 3 pour la liste exacte des valeurs organization_industries à injecter ici
  ],
  "reveal_personal_emails": false,
  "reveal_phone_number": false,
  "page": 1,
  "per_page": 25
}
```

> ⚠️ Ne pas ajouter `revenue_range` dans le body — non supporté, cause une erreur silencieuse
> ⚠️ Utiliser `organization_industries` (strings) et NON `organization_industry_tag_ids` (cause erreur 400)

**Réponse — champs disponibles (masqués) :**
```json
{
  "people": [
    {
      "id": "id_apollo_unique",
      "first_name": "Prénom",
      "last_name": "",
      "title": "Poste",
      "email": "",
      "linkedin_url": "",
      "organization": {
        "name": "Nom Entreprise",
        "industry": "secteur",
        "estimated_num_employees": 50,
        "annual_revenue": null,
        "founded_year": 2010,
        "website_url": "https://...",
        "city": "Paris",
        "country": "France"
      }
    }
  ]
}
```

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

## Filtres sectoriels validés — `organization_industries`

> Les valeurs exactes à utiliser dans `organization_industries` sont définies dans **`context.md` → SECTION 3**.
> Chaque secteur cible y contient son mot-clé Apollo exact (champ "Mots-clés Apollo").
> Ne jamais inventer une valeur ici — toujours lire la source.

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
| Erreur 400 paramètres | `organization_industry_tag_ids` utilisé | Remplacer par `organization_industries` |
| 429 | Rate limit | Attendre 60 secondes, réessayer |

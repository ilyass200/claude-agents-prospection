# Connecteur Apollo.io

## Présentation

Apollo.io est la plateforme de sourcing B2B utilisée par l'Agent Sourcing. Ce fichier contient les instructions exactes et validées pour appeler l'API Apollo correctement.

---

## Configuration

```
BASE_URL : https://api.apollo.io/api/v1
CLE_API  : $APOLLO_API_KEY  ← définie dans .env
```

> Pour configurer ta clé API Apollo :
> 1. Connecte-toi sur https://app.apollo.io
> 2. Va dans Settings → Integrations → API
> 3. Copie ta clé API (40+ caractères)
> 4. Ouvre `.env` et remplace la valeur de `APOLLO_API_KEY`
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

## Règle obligatoire avant toute révélation — Pré-qualification sur données masquées

> ⛔ **NE JAMAIS appeler `people/match` sans avoir vérifié les deux conditions ci-dessous.**
> Chaque appel coûte 1 crédit. Un crédit dépensé sur un lead non qualifié ou déjà dans le sheet est un crédit perdu définitivement.

### Condition 1 — Déduplication (0 crédit)

Avant tout, vérifier que l'entreprise n'est **pas déjà présente dans Google Sheets** :
- Lire la colonne H (entreprise) via `connectors/gsheets.md` → Endpoint 1 **une seule fois au début** et stocker la liste en mémoire
- Comparer `organization.name` (retourné par `api_search`) avec cette liste
- Si l'entreprise est déjà dans le sheet → **SKIP, 0 crédit, passer au suivant**

### Condition 2 — Pré-score sur données masquées (0 crédit)

Les données disponibles dans la réponse `api_search` sont **limitées** (flags booléens uniquement — pas de valeurs réelles) :

| Champ disponible | Ce qu'il indique |
|---|---|
| `organization.name` | Nom de l'entreprise |
| `organization.has_employee_count` | Apollo a des données sur la taille |
| `organization.has_revenue` | Apollo a des données sur le CA |
| Secteur | **Connu implicitement** depuis le `organization_industry_tag_id` utilisé dans le filtre |

> ⚠️ `industry`, `annual_revenue`, `estimated_num_employees`, `founded_year`, `website_url` **ne sont PAS disponibles** dans la réponse `api_search`. Ces champs n'arrivent qu'après révélation via `people/match`.

**Règle de pré-score — appliquer dans cet ordre :**

```
SI secteur = tag haute priorité (Immobilier, Hôtellerie, Restauration, Luxe → 25 pts ICP)
  → RÉVÉLER (secteur seul suffit à valider l'intérêt)

SINON SI secteur = tag priorité moyenne (Conseil, Comptabilité, Retail → 20 pts ICP)
  ET has_revenue = true
  → RÉVÉLER (revenue data existe → scoring réel possible après révélation)

SINON SI secteur = tag basse priorité (E-learning, Formation → 15 pts ICP)
  ET has_revenue = true
  → RÉVÉLER seulement si le quota n'est pas encore atteint

SINON
  → SKIP, 0 crédit
```

**Résumé :**
- Secteur haute priorité → toujours révéler (vaut le crédit)
- Secteur moyen/bas sans `has_revenue: true` → jamais révéler (trop risqué)

---

## Endpoint 2 — Révélation d'un contact `POST /api/v1/people/match`

> ⛔ N'appeler cet endpoint **que si les deux conditions de pré-qualification ci-dessus sont remplies**.
> Coûte **1 crédit/contact** — irreversible.

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

**Après révélation — vérifications immédiates avant de compter le lead :**
1. Email présent et non vide → sinon SKIP
2. Scorer avec les données complètes (Agent ICP Score)
3. Si score < $ICP_SCORE_MINIMUM → lead rejeté (crédit dépensé mais lead non ajouté au sheet)
4. Si score ≥ $ICP_SCORE_MINIMUM → ajouter au sheet

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

## Filtres sectoriels — `organization_industry_tag_ids`

> Les tag IDs à utiliser dans `organization_industry_tag_ids` sont **spécifiques à l'activité de chaque utilisateur** — ils sont définis dans `context.md` → SECTION 3, générée via `/setup`. Ce connecteur ne doit jamais coder en dur une liste de secteurs : ce qui est pertinent pour une activité ne l'est pas pour une autre.

> **Pour trouver un tag ID :** faire une recherche sur [app.apollo.io](https://app.apollo.io) avec le secteur souhaité en filtre "Industry", puis inspecter la requête réseau envoyée par l'interface — le champ `organization_industry_tag_ids` contient l'ID hexadécimal correspondant.

> Pour chercher dans **plusieurs secteurs cibles** en une seule requête, passer leurs tag IDs ensemble dans le tableau. Pour cibler un secteur précis, passer un seul tag ID.
> Si un secteur défini dans `context.md` n'a pas encore de tag ID renseigné (`[à compléter]`), ne pas lancer de recherche sur ce secteur tant qu'il n'est pas résolu — alerter l'Orchestrateur plutôt que d'improviser une valeur.

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

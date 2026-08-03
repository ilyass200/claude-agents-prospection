# Équipe de prospection — agents Claude Code

Un système de prospection B2B par email, entièrement piloté par [Claude Code](https://claude.com/claude-code) : un Orchestrateur délègue à 7 agents spécialisés (sourcing, scoring, rédaction, envoi, lecture des réponses, analyse, relance) qui exécutent eux-mêmes les appels API décrits dans des connecteurs. Aucun serveur à héberger, aucun code à maintenir — tout est piloté par des instructions markdown que Claude Code lit et exécute.

## Ce que ça fait

1. **Sourcing** — cherche des prospects sur Apollo.io selon tes secteurs cibles
2. **ICP Score** — note chaque lead (budget, secteur, signal de besoin, ancienneté)
3. **Enrichissement** — rédige un email personnalisé par lead, jamais un template générique
4. **Envoi** — programme l'envoi via Brevo, réparti sur plusieurs boîtes email (anti-spam)
5. **Fetch Replies** — lit les réponses reçues par IMAP et met à jour le tracking
6. **Analyse** — calcule les KPIs (taux de réponse, leads chauds, performance par secteur/sender)
7. **Relance** — rédige les relances pour les leads sans réponse, **toujours soumises à validation avant envoi**

Tout le tracking se fait dans un unique Google Sheet — pas de base de données à gérer.

## Prérequis

- [Claude Code](https://claude.com/claude-code) installé
- Un compte [Apollo.io](https://apollo.io) (sourcing de prospects)
- Un compte [Brevo](https://brevo.com) (envoi d'emails, clé API SMTP)
- Un projet Google Cloud avec l'API Google Sheets activée + un compte de service
- Une ou plusieurs boîtes email avec accès IMAP (Hostinger par défaut, adaptable)

## Installation

```bash
git clone <url-du-repo>
cd <dossier-du-repo>
claude
```

Puis, dans Claude Code, lance :

```
/setup
```

Cette commande t'interviewe (identité, offre, secteurs cibles, ton, clés API, boîtes d'envoi) et génère automatiquement tes trois fichiers personnels :

- `context.md` — ton référentiel business (positionnement, offres, secteurs, templates email)
- `.env` — tes clés API et paramètres de campagne
- `senders.json` — tes boîtes email d'envoi

Ces trois fichiers sont **dans `.gitignore`** : ils ne seront jamais commités, ni par toi ni accidentellement. Ce sont tes données personnelles, propres à ton activité.

### Configuration manuelle (alternative)

Si tu préfères ne pas utiliser `/setup`, copie les templates et remplis-les toi-même :

```bash
cp example.env .env
cp senders.example.json senders.json
cp context.example.md context.md
```

Édite ensuite ces trois fichiers en suivant les instructions en commentaire (`example.env`) ou les placeholders `[entre crochets]` (`context.example.md`, `senders.example.json`).

## Utilisation

Une fois configuré, parle simplement à l'Orchestrateur en langage naturel :

| Tu dis | Ce qui se passe |
|---|---|
| "Trouve-moi 20 leads dans l'immobilier" | Sourcing → ICP Score → Enrichissement, jusqu'à 20 leads qualifiés dans le Sheet |
| "Lance une campagne" | Sourcing → ICP Score → Enrichissement → **Envoi** |
| "Analyse mes résultats" | Fetch Replies → Analyse → rapport KPI complet |
| "Qui relancer ?" | Fetch Replies → Analyse → Relance → **emails affichés pour validation avant tout envoi** |
| "Envoie les relances" | Envoi des relances validées précédemment |

L'Orchestrateur ne lance jamais l'Agent Envoi sans une instruction explicite ("envoie", "lance la campagne") — chercher des leads ne déclenche jamais un envoi.

## Structure du projet

```
orchestrator.md          Le chef d'orchestre — reçoit tes instructions, décide quel agent lancer
agents/                  Un fichier par agent (sourcing, icp_score, enrichissement, envoi, fetch_replies, analyse, relance)
connectors/               Instructions d'appel API par service (Apollo, Brevo, Google Sheets, IMAP)
context.example.md       Template de ton référentiel business — génère ton context.md via /setup
example.env              Template de configuration — génère ton .env via /setup
senders.example.json     Template de tes boîtes d'envoi — génère ton senders.json via /setup
.claude/commands/setup.md   La commande /setup elle-même
```

## Sécurité

- `.env`, `senders.json`, `context.md` et `credentials/` sont gitignorés — ne les commite jamais.
- Les credentials (clés API, mots de passe IMAP) ne transitent que par la couche d'exécution des agents ; ils ne sont jamais affichés dans les rapports remontés à l'utilisateur.
- Si tu forkes ou clones un dépôt public basé sur ce projet, vérifie toujours qu'aucun fichier personnel n'a été commité par erreur avant de pousser tes propres changements.

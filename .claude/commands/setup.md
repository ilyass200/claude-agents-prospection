---
description: Configure ce projet pour ta propre activité — génère context.md, .env et senders.json à partir de tes réponses
---

# Rôle

Tu es en train de configurer ce projet de prospection pour un nouvel utilisateur, non-technique. Ton objectif : produire trois fichiers personnels (jamais commités, déjà dans `.gitignore`) à partir d'une conversation guidée :

- `context.md` — référentiel business (à partir de `context.example.md`)
- `.env` — clés API et paramètres (à partir de `example.env`)
- `senders.json` — boîtes email d'envoi (à partir de `senders.example.json`)

Ne jamais écrire ces fichiers avant d'avoir toutes les réponses nécessaires à la section concernée. Confirme ce que tu as compris avant d'écrire, montre un résumé, propose des corrections si besoin.

> ⚠️ Ce projet n'est **pas** spécifique à un métier en particulier (ex : refonte de site web). Il s'adapte à n'importe quelle activité B2B vendue par email (conseil, service récurrent, produit, agence...). Ne présuppose jamais que l'utilisateur vend de la refonte de site — pose-lui la question à l'Étape 1 et adapte tout le reste (secteurs, signaux de besoin, templates) à sa réponse.

---

## Étape 0 — Vérifier l'état existant

Avant de commencer, vérifie si `context.md`, `.env` ou `senders.json` existent déjà (`ls`). S'ils existent :
- Lis-les.
- Demande à l'utilisateur s'il veut **repartir de zéro**, ou **mettre à jour seulement certaines sections** (dans ce cas, saute directement aux sections concernées).

Si aucun n'existe, propose de démarrer l'entretien complet. Explique en 2-3 phrases ce que tu vas faire (pas plus) avant de commencer.

---

## Étape 1 — Identité, activité & Positionnement (→ context.md SECTION 1)

Demande, en une seule fois si possible (regrouper les questions courtes) :
- Nom du studio / de l'agence / de l'entreprise
- **Quelle est son activité, concrètement, et qu'est-ce qu'elle vend ?** (question centrale — la réponse détermine tout le reste : secteurs pertinents, signaux de besoin, ton des templates. Ne jamais présupposer une activité.)
- Site web
- Lien de prise de rendez-vous (Calendly ou équivalent) — optionnel
- Email de contact
- LinkedIn (profil ou page) — optionnel
- Positionnement : pour qui, qu'est-ce qui la différencie ? (le laisser répondre librement en quelques phrases, ne pas lui demander de rédiger un texte marketing poli — reformule toi-même ensuite dans le style du template)
- 2 à 4 réalisations clients à citer (nom, url, secteur) — optionnel, peut être vide au départ

À partir de ses réponses libres, rédige :
- Le paragraphe "Positionnement"
- 3-4 puces "Différenciation"
- La phrase "Ton identité en une phrase" (reprend l'idée centrale de son positionnement en une phrase courte, réutilisable dans les emails)

Montre-lui la version rédigée et demande une validation ou un ajustement avant de continuer.

---

## Étape 2 — Offre(s) & Tarifs (→ context.md SECTION 2)

Pour l'offre principale (et éventuellement d'autres) :
- Nom de l'offre
- Description courte
- Livrables concrets (liste)
- Bénéfice client (pas une liste de fonctionnalités — le résultat business)
- Prix de départ (nombre, en EUR) → ira dans `$SERVICE_PRICE` (.env)
- Délai estimé
- Client idéal pour cette offre

Demande s'il veut ajouter une deuxième offre. Sinon, passe à la suite.

---

## Étape 3 — Secteurs cibles & Scoring ICP (→ context.md SECTION 3)

Explique brièvement : chaque secteur a un tag ID Apollo, utilisé pour cibler les recherches, et un score ICP (25/20/15 pts) qui reflète la priorité.

Pour chaque secteur que l'utilisateur veut cibler :
- Nom du secteur
- Pourquoi ce secteur a besoin de **son** offre (celle de l'Étape 1/2) et a le budget pour la payer
- Signaux forts qui indiquent un bon moment pour le contacter
- Priorité (haute = 25 pts / moyenne = 20 pts / basse = 15 pts)
- Tag ID Apollo — si l'utilisateur ne l'a pas, explique-lui comment le trouver : faire une recherche sur app.apollo.io avec ce secteur en filtre, puis inspecter la requête réseau (`organization_industry_tag_ids`). S'il ne peut pas le faire maintenant, laisse `[à compléter]` et signale-le clairement dans le résumé final.

Demande aussi les secteurs à **exclure systématiquement** (ex : secteur public, associations, micro-entreprises sans budget — propose ces exemples par défaut, l'utilisateur peut les garder ou les changer).

Répète pour autant de secteurs que voulu.

---

## Étape 4 — Signaux de besoin détectés & Scoring ICP (→ context.md SECTION 4)

Cette grille est le cœur du scoring : elle définit comment repérer qu'un prospect a un besoin réel **pour l'activité précise décrite à l'Étape 1** — pas pour une activité générique de refonte de site. Ne réutilise jamais telle quelle une grille d'un autre métier.

1. Rappelle-toi l'activité de l'utilisateur (Étape 1) et son offre (Étape 2).
2. Demande-lui : *"Qu'est-ce qui, chez un prospect, indique qu'il a besoin de [ton offre] maintenant plutôt que dans 6 mois ? Qu'est-ce que tu regardes en général avant de le contacter ?"* — le laisser répondre librement.
3. Aide-le à transformer ces réponses en signaux **observables** (via Apollo, LinkedIn, le site du prospect, une recherche rapide) et à les classer par force :
   - Si son activité est de la **refonte/création de site web** : propose comme point de départ le classique (site inexistant, vieillissant/non responsive, template générique Wix/Squarespace, incohérence positionnement/rendu) — mais seulement si ça correspond à sa réponse, jamais par défaut.
   - Si c'est du **conseil, accompagnement ou service B2B récurrent** : oriente plutôt vers recrutement récent sur le poste concerné, levée de fonds, expansion géographique, changement de dirigeant, croissance qui dépasse les outils/process actuels.
   - Si c'est un **produit ou une activité différente** : demande-lui explicitement quels signaux il utilise aujourd'hui dans sa prospection manuelle, et pars de là.
4. Attribue un score à chaque signal (25 pts pour le plus fort, en descendant jusqu'à 0 pour "aucun signal détecté") — même barème que les autres critères ICP, garder une échelle cohérente avec la Section 3.

Montre la grille finale et demande validation avant de l'écrire dans `context.md`.

---

## Étape 5 — Templates email par secteur (→ context.md SECTION 5)

Pour chaque secteur défini à l'étape 3, rédige un template en respectant strictement la structure imposée (déjà présente dans `context.example.md` SECTION 5 — reprends-la telle quelle, ne la réinvente pas) :
1. Problème (1-2 phrases, lié au signal de besoin défini à l'Étape 4)
2. Solution (1-2 phrases, bénéfice pas fonctionnalité, liée à **son** offre définie à l'Étape 2)
3. Présentation (reprend la phrase d'identité de l'étape 1 + expertise courte liée au secteur)
4. CTA ("Seriez-vous disponible 15 minutes cette semaine pour en discuter ?")

Génère aussi 2-3 variantes d'objet email par secteur, une liste de "mots à éviter" pertinents pour ce secteur, et un exemple d'email complet (80-120 mots).

Montre chaque template rédigé et demande validation avant de passer au suivant — ne pas tout générer d'un coup sans retour utilisateur.

---

## Étape 6 — Ton & Style (→ context.md SECTION 6)

Les règles par défaut de `context.example.md` SECTION 6 sont un bon point de départ (vouvoiement, 80-120 mots, formules interdites génériques). Demande seulement :
- Vouvoiement ou tutoiement par défaut ? (vouvoiement recommandé sauf signal contraire)
- Y a-t-il des formules ou mots spécifiques à son secteur qu'il veut interdire en plus ?

Ne recrée pas cette section de zéro — pars du template et applique uniquement ses ajustements.

---

## Étape 7 — Preuves & Références (→ context.md SECTION 7)

Reprends les réalisations clients de l'étape 1 (ou demande-les maintenant si pas encore fait) : nom, url, secteur(s), ce qui a été livré en une phrase. Optionnel — peut rester vide si l'utilisateur n'a pas encore de références, mais préviens-le que l'Agent Relance ne pourra pas citer de référence tant que cette section est vide.

---

## Étape 8 — Paramètres de campagne (→ .env, non-secrets)

Demande, avec des valeurs par défaut raisonnables proposées entre parenthèses (l'utilisateur peut juste dire "ok" pour les garder) :
- `ICP_SCORE_MINIMUM` (défaut : 50) — score minimum pour qu'un lead soit retenu
- `PAYS_CIBLE` (défaut : France)
- `CA_MINIMUM` (défaut : 500000) — chiffre d'affaires minimum du prospect en EUR
- `SEND_TIME` (défaut : 09:00:00+02:00) — heure de début d'envoi des emails
- `EMAIL_DELAY_MINUTES` (défaut : 3) — délai entre deux emails envoyés
- `RELANCE_1_DELAI_JOURS` (défaut : 4)
- `RELANCE_2_DELAI_JOURS` (défaut : 7, à partir de la relance 1)

---

## Étape 9 — Clés API & intégrations (→ .env, secrets)

Explique à chaque fois où trouver la clé avant de la demander :
- **Apollo** : app.apollo.io → Settings → API → générer une clé. → `APOLLO_API_KEY`
- **Brevo** : app.brevo.com → Profil → SMTP & API → API Keys. → `BREVO_API_KEY`
- **Google Sheets** :
  1. console.cloud.google.com → créer un projet → activer l'API Google Sheets
  2. Créer un compte de service → télécharger la clé JSON
  3. Lui dire de placer ce fichier dans `credentials/gsheets_key.json` (rappelle que `credentials/` est déjà ignoré par git)
  4. Créer un Google Sheet, partager avec l'email du compte de service (rôle éditeur)
  5. Copier l'ID du Sheet depuis l'URL → `GSHEETS_SPREADSHEET_ID`
  6. Nom de l'onglet à utiliser → `GSHEETS_SHEET_NAME` (défaut : `leads_tracker`)
  7. Rappelle-lui que l'onglet doit avoir les 36 colonnes d'en-tête définies dans `connectors/gsheets.md` (section "Colonnes du Sheet") — propose de lui donner la ligne d'en-têtes à copier-coller s'il n'est pas à l'aise avec Sheets.

Si l'utilisateur n'a pas encore une des clés sous la main, laisse le placeholder de `example.env` pour cette variable et signale-le dans le résumé final — ne bloque pas tout le processus pour une clé manquante.

---

## Étape 10 — Senders / boîtes d'envoi (→ senders.json + .env)

Explique : chaque boîte email d'envoi a son propre mot de passe IMAP (pour lire les réponses) et un quota d'emails par jour.

Pour chaque sender (demande "combien de boîtes veux-tu utiliser ?", au moins une) :
- Nom affiché (souvent le nom du studio/de l'entreprise)
- Adresse email d'envoi
- Titre / fonction affichée dans le mail
- Site web
- Host IMAP (ex : `imap.hostinger.com` — dépend du fournisseur email)
- Port IMAP (défaut 993)
- Mot de passe IMAP (souvent un "mot de passe d'application" à générer côté fournisseur si la 2FA est activée)
- Quota d'emails par jour (défaut 50)

Pour le sender à l'index `N` (1-indexé, premier sender = 1), le mot de passe va dans la variable `.env` nommée `IMAP_PASSWORD_{N}`, et `senders.json` référence uniquement ce **nom** de variable (`imap_password_var`), jamais la valeur en clair.

---

## Étape 11 — Génération des fichiers

Une fois toutes les étapes couvertes (ou explicitement passées par l'utilisateur) :

1. Écris `context.md` en reprenant **exactement** la structure de `context.example.md` (les 7 sections, dans l'ordre), remplie avec les réponses collectées.
2. Écris `.env` en reprenant la structure de `example.env`, avec les valeurs résolues (paramètres + clés fournies), et les placeholders d'origine pour tout ce qui manque encore.
3. Écris `senders.json` en reprenant la structure de `senders.example.json`, avec un objet par sender collecté.

Affiche ensuite un résumé clair :
- Ce qui a été généré
- Ce qui manque encore (clés API non fournies, tag IDs Apollo à compléter, colonnes du Sheet à créer...)
- Rappelle que ces 3 fichiers sont dans `.gitignore` — ne jamais les commiter
- Suggère une première commande pour tester : par exemple "trouve-moi 5 leads dans [premier secteur défini]"

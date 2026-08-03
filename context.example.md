# Context — Référentiel Business

> Ce fichier est la **source unique de vérité** sur tes services, ton positionnement, tes secteurs
> cibles et tes templates de communication. Tous les agents y font référence.
> Ne jamais dupliquer ces informations dans les fichiers agents.

> 📌 Ce fichier est un **template**. Ne l'édite pas à la main si tu peux l'éviter : lance `/setup`
> dans Claude Code, réponds aux questions, et il générera ton propre `context.md` (ignoré par git,
> jamais commité) à partir de tes réponses.

---

## SECTION 1 — Identité & Positionnement

**Nom / Studio :** [Nom de ton studio/agence]
**Site :** [https://tonsite.com]
**Contact (Calendly ou autre lien de prise de RDV) :** [lien]
**Email :** [email de contact]
**LinkedIn :** [url profil ou page]

**Positionnement :**
[2-4 phrases décrivant ce que tu fais, pour qui, et ce qui te distingue. Exemple de structure :
"Expert [ton domaine], [Nom studio] conçoit des [ce que tu livres] qui allient [qualité 1],
[qualité 2] et [qualité 3]. Chaque projet est étudié en profondeur avant d'être livré."]

**Différenciation — ce que les autres ne font pas :**
- [Élément différenciant 1]
- [Élément différenciant 2]
- [Élément différenciant 3]
- Résultat : [ce que ça change concrètement pour le client]

**Ton identité en une phrase (à utiliser dans les emails) :**
"[Une phrase qui résume ta proposition de valeur, réutilisée dans le bloc PRÉSENTATION des emails]"

**Réalisations notables (références clients) :**
- [NOM CLIENT 1] → [url]
- [NOM CLIENT 2] → [url]
- [NOM CLIENT 3] → [url]

---

## SECTION 2 — Offres & Tarifs

### Offre 01 — [Nom de ton offre principale]

**Description :**
[Ce que couvre cette offre, en 2-3 phrases.]

**Livrables concrets :**
- [Livrable 1]
- [Livrable 2]
- [Livrable 3]

**Bénéfice client :**
[Ce que le client obtient concrètement — résultat business, pas fonctionnalité technique.]

**Prix de départ :** $SERVICE_PRICE EUR
**Délai estimé :** [X à Y semaines]
**Idéal pour :** [Type d'entreprise ou de profil qui bénéficie le plus de cette offre]

> Ajoute d'autres offres si nécessaire en dupliquant cette structure (Offre 02, Offre 03...).

---

## SECTION 3 — Secteurs cibles & Scoring ICP

> Pour chaque secteur, tu as besoin du **tag ID Apollo** correspondant (`organization_industry_tag_ids`).
> Pour le trouver : fais une recherche sur [app.apollo.io](https://app.apollo.io) avec le filtre secteur
> souhaité, puis inspecte la requête réseau (`organization_industry_tag_ids` dans le payload).

### Secteurs PRIORITÉ HAUTE (25 pts ICP)

**[Nom du secteur]**
- Pourquoi : [Pourquoi ce secteur a un besoin fort et un budget pour ton offre]
- Signaux forts : [Signal 1, signal 2, signal 3]
- Tag ID Apollo : `[tag_id]`

---

### Secteurs PRIORITÉ MOYENNE (20 pts ICP)

**[Nom du secteur]**
- Pourquoi : [...]
- Signaux forts : [...]
- Tag ID Apollo : `[tag_id]`

---

### Secteurs PRIORITÉ BASSE (15 pts ICP)

**[Nom du secteur]**
- Pourquoi : [...]
- Signaux forts : [...]
- Tag ID Apollo : `[tag_id]`

---

### Secteurs EXCLUS (score éliminatoire — ne jamais prospecter)

- [Secteur ou type d'entreprise à toujours exclure, ex : secteur public, associations, micro-entreprises sans budget...]

---

## SECTION 4 — Signaux de besoin détectés

> Cette grille définit comment repérer, pour **ton** offre spécifique, qu'une entreprise a un besoin
> réel maintenant plutôt que dans 6 mois. Le principe : un signal fort et facilement observable
> (via Apollo, LinkedIn, le site du prospect...) = plus de points. Un signal faible ou générique
> = moins de points. Aucun signal détecté = 0 pt.
>
> Réfléchis à ce qui, dans **ton** métier, indique qu'un prospect a un besoin urgent ou latent.
> Quelques exemples pour t'aider à démarrer :
> - Si tu vends de la **refonte de site web** : absence de site, site vieillissant/non responsive,
>   template générique (Wix/Squarespace visible), incohérence entre le positionnement et le rendu du site
> - Si tu vends du **conseil / accompagnement** : recrutement récent sur le poste concerné, levée de
>   fonds, expansion géographique, changement de dirigeant
> - Si tu vends un **produit ou service récurrent** : signes d'insatisfaction envers un concurrent,
>   croissance rapide qui rend l'ancienne solution insuffisante, changement réglementaire à absorber
>
> Remplis le tableau ci-dessous avec **tes propres signaux**, du plus fort (le plus de points) au
> plus faible :

| Signal détecté | Score | Comment le détecter |
|---|---|---|
| [Signal le plus fort pour ton offre] | 25 pts | [Où et comment le repérer concrètement] |
| [Signal fort] | 20 pts | [...] |
| [Signal moyen] | 15 pts | [...] |
| [Signal faible / bonus] | 10 pts | [...] |
| Aucun signal détecté | 0 pts | [Ce qui caractérise un prospect sans besoin visible] |

---

## SECTION 5 — Templates email par secteur

### Structure obligatoire — À respecter pour chaque email, chaque secteur

```
BLOC 1 — PROBLÈME (1-2 phrases)
→ Identifier et nommer le problème spécifique de l'entreprise
→ S'appuyer sur le signal détecté (context.md SECTION 4) et les données du lead
→ Être direct et factuel — pas d'entrée en matière creuse

BLOC 2 — SOLUTION (1-2 phrases)
→ Ce que le service peut apporter concrètement à cette entreprise
→ Rester lié au problème évoqué juste avant — pas de liste de fonctionnalités
→ Parler bénéfice, pas technique

BLOC 3 — PRÉSENTATION (1 phrase obligatoire)
→ Reprendre la formule définie en SECTION 1 ("Ton identité en une phrase"),
  adaptée avec une expertise courte liée au secteur du lead
→ La présentation vient APRÈS la valeur, jamais en ouverture

BLOC 4 — CTA (1 phrase)
→ "Seriez-vous disponible 15 minutes cette semaine pour en discuter ?"
→ Une seule question, sans pression, sans alternative
```

---

### Template — [Nom du secteur]

**Angle d'accroche :**
[Le fil conducteur psychologique de ce secteur — pourquoi ton offre compte pour lui spécifiquement.]

**Objets email (choisir selon le contexte du lead) :**
- "PROPOSITION — [angle] · [Nom entreprise]"
- "Suggestion — [angle] pour [Nom entreprise]"

**Éléments de langage clés :**
- "[expression 1]"
- "[expression 2]"

**Mots à éviter :**
- "[mot trop technique ou générique pour ce secteur]"

**Exemple d'email complet :**
```
[Prénom],

[BLOC 1 — problème spécifique au secteur]

[BLOC 2 — solution / bénéfice]

[BLOC 3 — présentation, cf. SECTION 1]

[BLOC 4 — CTA]
```

> Duplique ce bloc pour chaque secteur défini en SECTION 3.

---

## SECTION 6 — Ton & Style de communication

**Ton général :** Professionnel, direct, orienté valeur pour le prospect. Jamais vendeur ou agressif. On parle en pair à pair, pas en commercial.

**Vouvoiement / Tutoiement :** Vouvoiement par défaut dans tous les secteurs. Ne jamais tutoyer sans signal fort (startup, tech, fondateur jeune actif sur les réseaux).

**Longueur cible :** 80 à 120 mots maximum par email. Chaque mot doit avoir sa raison d'être.

**Formules INTERDITES — ne jamais utiliser :**
- "Je me permets de vous contacter"
- "Dans le cadre d'une possible collaboration"
- "N'hésitez pas à me contacter"
- "En espérant que ce message vous trouvera en bonne santé"
- "Je serais ravi de..."
- "Notre agence propose..."
- "Nous serions heureux de..."
- "Suite à votre profil consulté sur LinkedIn"
- Toute formule de politesse creuse en ouverture

**Ce que chaque email doit obligatoirement contenir :**
- Une référence spécifique à l'entreprise ou au prospect (nom, secteur, signal détecté)
- Un problème ou une opportunité clairement identifiée et formulée
- Un bénéfice concret lié au service (pas une liste de fonctionnalités)
- Un seul appel à l'action : demander 15 minutes, pas plus

**Règle d'or :** Si l'email pourrait être envoyé à 100 autres personnes sans changer un mot, il est mauvais. Chaque email doit sonner comme écrit spécifiquement pour cette personne.

---

## SECTION 7 — Preuves & Références

**Réalisations disponibles comme preuves sociales :**

- **[NOM CLIENT]** ([url]) — Secteur : "[secteur 1]", "[secteur 2]". [Ce qui a été livré en une phrase.]

> Ajoute une ligne par référence client. L'Agent Relance n'utilise une référence que si son secteur
> correspond à celui du lead — ne jamais en inventer une.

**Phrases clés réutilisables par secteur :**
- Général : "[phrase de crédibilité générique réutilisable]"

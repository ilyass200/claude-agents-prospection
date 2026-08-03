# Connecteur Brevo (ex-Sendinblue)

## Présentation

Brevo est la plateforme d'envoi d'emails utilisée par l'Agent Envoi. Ce fichier contient toutes les instructions pour appeler l'API Brevo correctement.

---

## Configuration

```
BASE_URL : https://api.brevo.com/v3
CLE_API  : $BREVO_API_KEY  ← clé unique partagée par tous les senders, définie dans .env
```

> Tous les senders (adresses expéditrices) sont vérifiés sur le **même compte Brevo**. La clé API est donc unique et globale — seul le champ `sender` (name + email) change d'un sender à l'autre dans le body des appels.

---

## Endpoints utilisés

### 1. Envoi d'un email transactionnel — `POST /smtp/email`

Envoie un email simple en texte brut (recommandé pour la prospection — meilleure délivrabilité).

**Requête complète :**
```json
POST https://api.brevo.com/v3/smtp/email
Headers:
  Content-Type: application/json
  api-key: $BREVO_API_KEY

Body:
{
  "sender": {
    "name": "{sender.name}",
    "email": "{sender.email}"
  },
  "to": [
    {
      "email": "prospect@entreprise.com",
      "name": "Prénom Nom Prospect"
    }
  ],
  "subject": "Objet de l'email",
  "textContent": "[Corps de l'email — lu depuis la colonne corps_email du Google Sheet]",
  "scheduledAt": "[datetime calculé — voir règle ci-dessous]"
}
```

> **Règle de calcul du `scheduledAt` :**
> 1. Lire `$SEND_TIME` depuis `.env` (ex: `09:00:00+02:00`)
> 2. Prendre la date du jour (ex: `2026-04-07`)
> 3. Si l'heure actuelle est **avant** `$SEND_TIME` → `scheduledAt = aujourd'hui T $SEND_TIME`
> 4. Si l'heure actuelle est **après** `$SEND_TIME` → `scheduledAt = demain T $SEND_TIME`
> 5. Format final : `YYYY-MM-DDTHH:MM:SS+HH:MM` (ex: `2026-04-07T09:00:00+02:00`)
>
> Si `$SEND_TIME` n'est pas défini → envoyer immédiatement (ne pas inclure `scheduledAt` dans le body).

**Codes de succès :**
- `200` ou `201` → envoi immédiat accepté
- `202` → envoi schedulé accepté (c'est le code normal quand `scheduledAt` est fourni)

> ⚠️ Ne jamais traiter le 202 comme une erreur — c'est le retour attendu pour tout envoi avec `scheduledAt`.

**Réponse en cas de succès (200, 201 ou 202) :**
```json
{
  "messageId": "<unique-message-id@smtp-relay.mailin.fr>"
}
```
→ Stocker ce `messageId` dans le tracking pour le suivi.

---

### 2. Vérification historique d'envoi — `GET /smtp/emails?email={email}`

Utilisé par : Agent Envoi (vérification pré-envoi — source de vérité absolue)

```bash
curl -s -X GET \
  "https://api.brevo.com/v3/smtp/emails?email=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("email@exemple.com"))')&limit=1&sort=desc" \
  -H "api-key: $BREVO_API_KEY"
```

**Logique de décision :**

| Réponse | Signification | Action |
|---|---|---|
| `transactionalEmails` non vide | Contact déjà contacté au moins une fois | ⛔ Statut `"Déjà contacté"`, skip |
| `transactionalEmails` vide `[]` | Jamais contacté | ✅ Procéder |
| Erreur 5xx | Brevo indisponible | ⚠️ Procéder quand même |

> C'est la vérification la plus fiable car elle s'appuie sur l'historique réel de Brevo, indépendamment du sheet.

---

### 3. Vérification statut contact — `GET /contacts/{email}`

Utilisé par : Agent Envoi (vérification pré-envoi obligatoire)

```bash
curl -s -X GET \
  "https://api.brevo.com/v3/contacts/$(python3 -c 'import urllib.parse; print(urllib.parse.quote("email@exemple.com"))')" \
  -H "api-key: $BREVO_API_KEY"
```

**Réponses possibles :**

| Code | Signification | Action |
|---|---|---|
| `404` | Contact inconnu — nouveau prospect | ✅ Procéder à l'envoi |
| `200` + `emailBlacklisted: true` | Adresse blacklistée | ⛔ Statut `"Bloqué — blacklist"` |
| `200` + `emailBlacklisted: false` | Contact connu et actif | ✅ Procéder à l'envoi |
| `5xx` | Brevo indisponible | ⚠️ Procéder quand même |

**Exemple de réponse 200 :**
```json
{
  "email": "contact@entreprise.com",
  "emailBlacklisted": false,
  "smsBlacklisted": false,
  "createdAt": "2026-04-06T09:00:00Z",
  "modifiedAt": "2026-04-06T09:00:00Z",
  "attributes": {}
}
```

---

### 4. Suivi d'un email — `GET /smtp/emails`

Récupère les statistiques d'envoi (ouvertures, clics, bounces).

```
GET https://api.brevo.com/v3/smtp/emails?messageId=[ID_MESSAGE]
Headers:
  api-key: $BREVO_API_KEY
```

**Champs utiles retournés :**
- `events[].event` → `delivered`, `opened`, `clicked`, `bounced`, `spam`
- `events[].date` → Date de l'événement

---

### 5. Liste des événements par email — `GET /smtp/statistics/events`

Pour récupérer tous les événements d'une campagne (utile pour l'Agent Analyse & Relance).

```
GET https://api.brevo.com/v3/smtp/statistics/events?limit=50&event=opened
Headers:
  api-key: $BREVO_API_KEY
```

**Événements disponibles :**
| Event | Signification |
|---|---|
| `delivered` | Email reçu par le serveur destinataire |
| `opened` | Email ouvert par le prospect |
| `clicked` | Lien cliqué dans l'email |
| `softBounce` | Échec temporaire (boîte pleine) |
| `hardBounce` | Adresse email invalide |
| `spam` | Signalé comme spam |
| `unsubscribed` | Désabonnement |

---

## Bonnes pratiques de délivrabilité

### Configuration recommandée
- Utiliser un **domaine personnalisé** (pas Gmail/Hotmail)
- Configurer **SPF, DKIM et DMARC** sur ton domaine
- Ne jamais envoyer depuis une adresse `noreply@`

### Limites plan gratuit Brevo
- **300 emails/jour** (suffisant pour démarrer)
- Pas de limite mensuelle sur le plan gratuit
- Logo Brevo en bas des emails HTML (pas de problème en texte brut)

### Règles anti-spam
- Toujours envoyer en **texte brut** pour la prospection à froid
- Éviter les mots spam : "gratuit", "offre limitée", "urgent", "cliquez ici"
- Espacer les envois de 2 à 5 minutes entre chaque email
- Maximum `sender.max_emails_par_jour` emails/jour par sender en démarrage (warm-up du domaine)

---

## Warm-up recommandé (si nouveau domaine)

| Semaine | Emails/jour |
|---|---|
| Semaine 1 | 10/jour |
| Semaine 2 | 20/jour |
| Semaine 3 | 35/jour |
| Semaine 4+ | `sender.max_emails_par_jour` max (défini dans `senders.json`) |

---

## Codes d'erreur courants

| Code | Signification | Action |
|---|---|---|
| 401 | Clé API invalide | Vérifier la clé dans la config |
| 400 | Paramètre manquant ou invalide | Vérifier le body |
| 429 | Trop de requêtes | Attendre 1 minute, réessayer |
| 402 | Quota journalier atteint | Reprendre le lendemain |

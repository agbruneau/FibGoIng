# Rate Limiting et Throttling

## Résumé

Le **rate limiting** limite le nombre de requêtes qu'un client peut faire dans une période donnée. Il protège les services contre la surcharge et garantit une répartition équitable des ressources.

## Pourquoi Rate Limiting ?

### Protection contre

- **Attaques DDoS** : Trop de requêtes malveillantes
- **Bugs clients** : Boucle infinie appelant l'API
- **Abus** : Client consommant toutes les ressources
- **Surcharge** : Pic de trafic inattendu

### Garantir

- **Disponibilité** : Service toujours répondant
- **Équité** : Tous les clients ont leur part
- **SLA** : Respect des engagements de service

## Algorithmes de Rate Limiting

### Token Bucket

Le client a un "seau" de tokens, chaque requête consomme un token. Le seau se remplit à un rythme constant.

```
Configuration:
- Capacité: 100 tokens
- Remplissage: 10 tokens/seconde

Comportement:
- Requête arrive → consomme 1 token
- Seau vide → requête rejetée (429)
- Permet les bursts jusqu'à la capacité

Timeline:
T0:   Seau = 100 tokens
T0.1: 50 requêtes → Seau = 50
T1:   Remplissage +10 → Seau = 60
T1.1: 60 requêtes → Seau = 0
T1.2: 1 requête → REJECTED 429
T2:   Remplissage +10 → Seau = 10
```

**Avantages** : Permet les bursts, lissage naturel
**Usage** : Le plus courant en production

### Leaky Bucket

Les requêtes entrent dans un seau qui "fuit" à débit constant. Si le seau déborde, requête rejetée.

```
         Requêtes
            ↓
      ┌───────────┐
      │           │ Capacité max
      │  Seau     │
      │           │
      └─────┬─────┘
            │
            ↓ Débit constant
         Traitement
```

**Avantages** : Débit constant en sortie
**Usage** : Quand on veut lisser complètement le trafic

### Fixed Window

Compteur remis à zéro à intervalles fixes.

```
10:00:00 - 10:00:59 : Max 100 requêtes
10:01:00 - 10:01:59 : Max 100 requêtes (reset)

Problème : Burst de 200 requêtes possibles autour de la limite
10:00:59 : 100 requêtes
10:01:00 : 100 requêtes
= 200 en 2 secondes
```

**Avantages** : Simple à implémenter
**Inconvénients** : Problème des limites de fenêtre

### Sliding Window

Fenêtre glissante pour éviter les bursts aux limites.

```
À T=10:01:30, on compte les requêtes des 60 dernières secondes
(10:00:30 → 10:01:30)

Pas de reset brutal, limite toujours respectée.
```

**Avantages** : Pas de problème de limite
**Inconvénients** : Plus complexe à implémenter

## Configuration par Client

### Différents quotas selon le client

```yaml
rate_limits:
  # Partenaires premium
  - client_type: partner_premium
    requests_per_minute: 5000
    requests_per_day: 500000
    burst: 200

  # Partenaires standard
  - client_type: partner_standard
    requests_per_minute: 1000
    requests_per_day: 100000
    burst: 50

  # Application mobile
  - client_type: mobile_user
    requests_per_minute: 100
    requests_per_hour: 1000
    burst: 20
```

### Par endpoint

```yaml
endpoints:
  # Création de devis : coûteux
  - path: POST /quotes
    rate_limit:
      requests_per_minute: 100

  # Lecture : moins contraignant
  - path: GET /quotes/*
    rate_limit:
      requests_per_minute: 1000

  # Health check : pas de limite
  - path: GET /health
    rate_limit: none
```

## Réponse HTTP 429

Quand la limite est atteinte :

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642435200

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Trop de requêtes, réessayez dans 30 secondes",
    "retry_after": 30
  }
}
```

### Headers Standards

| Header | Description |
|--------|-------------|
| X-RateLimit-Limit | Limite maximale |
| X-RateLimit-Remaining | Requêtes restantes |
| X-RateLimit-Reset | Timestamp du reset |
| Retry-After | Secondes à attendre |

## Implémentation

### Avec Redis (distribué)

```python
import redis
from fastapi import Request, HTTPException

redis_client = redis.Redis()

async def rate_limit_middleware(request: Request, call_next):
    client_id = get_client_id(request)
    key = f"rate_limit:{client_id}"

    # Atomic increment avec expiration
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, 60)  # 1 minute

    if current > 100:  # Limite
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(100 - current)
    return response
```

## Cas Assurance

### Scénario : Comparateur de prix

Un comparateur appelle l'API pour obtenir des devis.

```yaml
# Configuration pour comparateurs
comparator_limits:
  # Limite globale
  global:
    requests_per_minute: 3000

  # Limite par endpoint
  endpoints:
    POST /quotes:
      requests_per_minute: 500
      cost: 10  # Coûte 10 tokens (opération coûteuse)

    GET /quotes/{id}:
      requests_per_minute: 2000
      cost: 1

  # Limite par produit (évite l'abus sur un produit)
  per_product:
    AUTO:
      requests_per_hour: 1000
    HABITATION:
      requests_per_hour: 1000
```

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| Headers | Toujours retourner les headers de rate limit |
| Documentation | Documenter clairement les limites |
| Alerting | Alerter quand un client approche sa limite |
| Graceful degradation | Réduire les features avant de rejeter |
| Monitoring | Suivre les taux de rejection |

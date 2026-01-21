# Rate Limiting

## Objectif pédagogique

Implémenter et configurer des stratégies de limitation de débit.

## Pourquoi rate limiter ?

- **Protection** : Éviter la surcharge des services
- **Équité** : Partager les ressources entre clients
- **Coût** : Contrôler la consommation des APIs payantes
- **Sécurité** : Mitiger les attaques DDoS

## Algorithmes de Rate Limiting

### Fixed Window

```
Fenêtre: 1 minute
Limite: 100 requêtes

[00:00 - 00:59] → Max 100 requêtes
[01:00 - 01:59] → Compteur reset, Max 100 requêtes
```

**Problème** : Pic à la frontière (burst de 200 entre 00:59 et 01:01)

### Sliding Window

```
À chaque instant, on compte les requêtes des 60 dernières secondes
```

Plus précis mais plus coûteux en mémoire.

### Token Bucket

```
┌──────────────────┐
│ Bucket (10 tokens)│
│    ●●●●●●●●      │  ← Tokens disponibles
└────────┬─────────┘
         │
   Refill: 5 tokens/seconde

Requête arrive:
  - Token dispo? → Consomme 1 token, traite
  - Pas de token? → Rejeté (429)
```

**Avantage** : Permet les bursts contrôlés.

### Leaky Bucket

```
┌──────────────────┐
│ Queue (10 slots) │
│ ▼▼▼▼▼▼           │  ← Requêtes en attente
└────────┬─────────┘
         │
   Fuite: 5 requêtes/seconde

Requête arrive:
  - Place dispo? → Mise en queue
  - Queue pleine? → Rejetée (429)
```

**Avantage** : Débit sortant constant.

## Implémentation Python

```python
import time
from typing import Dict, Tuple

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens par seconde
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        # Refill tokens
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class RateLimiter:
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}

    def check(self, client_id: str, capacity: int = 100,
              refill_rate: float = 10) -> Tuple[bool, dict]:
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(capacity, refill_rate)

        bucket = self.buckets[client_id]
        allowed = bucket.consume()

        return allowed, {
            "X-RateLimit-Limit": capacity,
            "X-RateLimit-Remaining": int(bucket.tokens),
            "X-RateLimit-Reset": int(bucket.last_update + bucket.capacity / refill_rate)
        }
```

## Headers de réponse

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200

HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067200
Retry-After: 30
```

## Stratégies par cas d'usage

### Par client (API Key)

```yaml
rate_limits:
  default: 100/minute
  clients:
    premium-partner: 10000/minute
    free-tier: 50/minute
```

### Par endpoint

```yaml
rate_limits:
  endpoints:
    GET /quotes: 200/minute      # Lecture = permissif
    POST /quotes: 50/minute      # Création = restrictif
    POST /claims: 20/minute      # Sinistres = très restrictif
```

### Quotas journaliers

```yaml
quotas:
  clients:
    partner-a:
      daily: 100000
      monthly: 2000000
```

## Réponse 429 enrichie

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Vous avez dépassé la limite de requêtes",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "retry_after": 30
    }
  }
}
```

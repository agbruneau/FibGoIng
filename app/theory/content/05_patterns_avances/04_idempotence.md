# Idempotence et Retry

## Résumé

L'**idempotence** garantit qu'une opération peut être exécutée plusieurs fois avec le même résultat. C'est crucial pour la fiabilité des systèmes distribués où les retries sont fréquents.

## Problématique

Dans un système distribué :
- Les réseaux sont instables
- Les requêtes peuvent timeout
- Les clients font des retry automatiques

**Sans idempotence :**

```
Client → POST /invoices (crée facture)
         ← Timeout (pas de réponse)
Client → POST /invoices (retry)
         ← 201 Created

Résultat : 2 factures créées au lieu d'1 !
```

## Qu'est-ce que l'Idempotence ?

Une opération est **idempotente** si :
```
f(x) = f(f(x)) = f(f(f(x))) = ...
```

Exécuter une fois ou plusieurs fois donne le même résultat.

### Verbes HTTP et Idempotence

| Méthode | Idempotent | Safe | Description |
|---------|------------|------|-------------|
| GET | Oui | Oui | Lecture seule |
| HEAD | Oui | Oui | Comme GET sans body |
| OPTIONS | Oui | Oui | Métadonnées |
| PUT | Oui | Non | Remplacement complet |
| DELETE | Oui | Non | Suppression |
| POST | **Non** | Non | Création |
| PATCH | Non* | Non | Modification partielle |

**Note :** POST n'est pas idempotent par nature, mais peut être rendu idempotent.

## Rendre POST Idempotent

### Idempotency Key

Le client fournit une clé unique par opération.

```http
POST /invoices
Idempotency-Key: inv-req-abc123

{
  "policy_number": "POL-001",
  "amount": 850.00
}
```

**Comportement serveur :**

```python
async def create_invoice(request: InvoiceRequest, idempotency_key: str):
    # Vérifier si déjà traité
    existing = await cache.get(f"idempotency:{idempotency_key}")

    if existing:
        # Retourner le résultat précédent
        return existing

    # Traiter la requête
    invoice = await billing.create_invoice(request)

    # Sauvegarder le résultat avec la clé
    await cache.set(
        f"idempotency:{idempotency_key}",
        invoice,
        ttl=86400  # 24h
    )

    return invoice
```

### Design de la Clé

La clé doit être :
- **Unique** par opération intentionnelle
- **Stable** pour les retry de la même opération
- **Générée côté client**

```python
# Bonnes pratiques
idempotency_key = f"{client_id}:{operation}:{uuid4()}"
# ou
idempotency_key = f"{client_id}:{hash(request_body)}:{timestamp}"
```

## Implémentation Complète

### Middleware Idempotency

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import json

class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.redis = redis_client
        self.ttl = 86400  # 24 heures

    async def dispatch(self, request: Request, call_next):
        # Uniquement pour les méthodes non-idempotentes
        if request.method not in ["POST", "PATCH"]:
            return await call_next(request)

        # Récupérer la clé
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        cache_key = f"idempotency:{idempotency_key}"

        # Vérifier si déjà traité
        cached = self.redis.get(cache_key)
        if cached:
            cached_response = json.loads(cached)
            return Response(
                content=cached_response["body"],
                status_code=cached_response["status"],
                headers={
                    **cached_response["headers"],
                    "X-Idempotency-Replayed": "true"
                }
            )

        # Vérifier si en cours de traitement (lock)
        lock_key = f"idempotency:lock:{idempotency_key}"
        if not self.redis.setnx(lock_key, "1"):
            return Response(
                content='{"error": "Request already in progress"}',
                status_code=409,
                headers={"Retry-After": "5"}
            )
        self.redis.expire(lock_key, 30)  # Lock de 30 secondes

        try:
            # Traiter la requête
            response = await call_next(request)

            # Cacher le résultat si succès (2xx)
            if 200 <= response.status_code < 300:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                self.redis.setex(
                    cache_key,
                    self.ttl,
                    json.dumps({
                        "status": response.status_code,
                        "headers": dict(response.headers),
                        "body": body.decode()
                    })
                )

                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

            return response

        finally:
            self.redis.delete(lock_key)
```

## Stratégies de Retry

### Retry avec Backoff Exponentiel

```python
import asyncio
import random

async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True
):
    """Exécute avec retry et backoff exponentiel."""

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except RetryableError as e:
            last_exception = e

            if attempt == max_retries:
                raise

            # Calcul du délai avec backoff exponentiel
            delay = min(base_delay * (2 ** attempt), max_delay)

            # Ajouter du jitter pour éviter les thundering herds
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    raise last_exception
```

### Erreurs Retryables vs Non-Retryables

```python
class RetryableError(Exception):
    """Erreur qui mérite un retry."""
    pass

def is_retryable(error: Exception) -> bool:
    """Détermine si l'erreur mérite un retry."""

    # Erreurs réseau
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    # Codes HTTP retryables
    if isinstance(error, HTTPError):
        retryable_codes = [408, 429, 500, 502, 503, 504]
        return error.status_code in retryable_codes

    # Ne pas retry les erreurs client (4xx sauf exceptions)
    return False
```

## Cas Assurance

### Création de Police (POST idempotent)

```python
@router.post("/policies", status_code=201)
async def create_policy(
    request: PolicyRequest,
    idempotency_key: str = Header(alias="Idempotency-Key")
):
    """
    Crée une police avec garantie d'idempotence.

    Headers:
        Idempotency-Key: Clé unique pour cette requête
    """
    # L'idempotence est gérée par le middleware
    policy = await policy_admin.create(
        customer_id=request.customer_id,
        product=request.product,
        quote_id=request.quote_id
    )

    return policy
```

### Paiement (Critique)

```python
@router.post("/invoices/{invoice_id}/payment")
async def record_payment(
    invoice_id: str,
    payment: PaymentRequest,
    idempotency_key: str = Header(alias="Idempotency-Key")
):
    """
    Enregistre un paiement.

    IMPORTANT: L'idempotency key est OBLIGATOIRE pour éviter
    les doubles paiements.
    """
    if not idempotency_key:
        raise HTTPException(
            400,
            "Idempotency-Key header required for payments"
        )

    return await billing.record_payment(
        invoice_id=invoice_id,
        amount=payment.amount,
        method=payment.method,
        idempotency_key=idempotency_key
    )
```

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| TTL adapté | Garder les résultats assez longtemps |
| Lock pendant traitement | Éviter les exécutions parallèles |
| Jitter | Ajouter de l'aléatoire dans les délais |
| Retryable vs non | Distinguer les erreurs |
| Client-side key | Le client génère la clé |
| Logging | Tracer les retries et replays |

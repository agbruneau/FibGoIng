# Stratégies de Cache

## Résumé

Le **caching** stocke temporairement les résultats d'opérations coûteuses pour améliorer les performances et réduire la charge sur les systèmes backend.

## Pourquoi Cacher ?

- **Performance** : Réponses plus rapides (ms vs secondes)
- **Coût** : Moins d'appels aux services backend
- **Résilience** : Données disponibles même si backend down
- **Scalabilité** : Absorber les pics de charge

## Types de Cache

### Cache Local (In-Memory)

Dans le processus de l'application.

```python
from functools import lru_cache
from cachetools import TTLCache

# LRU Cache simple
@lru_cache(maxsize=1000)
def get_product_config(product_id: str) -> dict:
    return load_from_db(product_id)

# Cache avec TTL
cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

def get_customer(customer_id: str) -> dict:
    if customer_id in cache:
        return cache[customer_id]

    customer = customer_hub.get(customer_id)
    cache[customer_id] = customer
    return customer
```

**Avantages** : Très rapide, pas de réseau
**Inconvénients** : Pas partagé, perdu au restart

### Cache Distribué (Redis/Memcached)

Partagé entre toutes les instances.

```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379)

async def get_policy(policy_number: str) -> dict:
    # Vérifier le cache
    cached = redis_client.get(f"policy:{policy_number}")
    if cached:
        return json.loads(cached)

    # Charger depuis la source
    policy = await policy_admin.get(policy_number)

    # Mettre en cache
    redis_client.setex(
        f"policy:{policy_number}",
        300,  # TTL 5 minutes
        json.dumps(policy)
    )

    return policy
```

**Avantages** : Partagé, persistant
**Inconvénients** : Latence réseau, complexité

### Cache HTTP

Au niveau du navigateur ou CDN.

```python
from fastapi import Response

@router.get("/products/{product_id}")
async def get_product(product_id: str, response: Response):
    product = await load_product(product_id)

    # Headers de cache HTTP
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["ETag"] = f'"{product["version"]}"'

    return product
```

## Stratégies d'Invalidation

### TTL (Time To Live)

Les données expirent après un délai fixe.

```python
# Cache pendant 5 minutes
redis_client.setex("key", 300, value)
```

**Usage** : Données qui peuvent être légèrement obsolètes

### Write-Through

Mise à jour du cache à chaque écriture.

```python
async def update_customer(customer_id: str, data: dict):
    # Mettre à jour la source
    updated = await customer_hub.update(customer_id, data)

    # Mettre à jour le cache immédiatement
    redis_client.setex(
        f"customer:{customer_id}",
        300,
        json.dumps(updated)
    )

    return updated
```

### Write-Behind (Write-Back)

Écriture asynchrone vers la source.

```python
async def update_customer_async(customer_id: str, data: dict):
    # Mettre à jour le cache immédiatement
    redis_client.setex(f"customer:{customer_id}", 300, json.dumps(data))

    # Écriture asynchrone vers la source
    await message_queue.publish("customer_updates", {
        "customer_id": customer_id,
        "data": data
    })
```

### Cache-Aside (Lazy Loading)

Charger dans le cache uniquement à la demande.

```python
async def get_with_cache_aside(key: str, loader):
    # 1. Vérifier le cache
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    # 2. Cache miss : charger depuis la source
    value = await loader()

    # 3. Stocker dans le cache
    redis_client.setex(key, 300, json.dumps(value))

    return value
```

### Invalidation Explicite

Invalider quand les données changent.

```python
async def update_policy(policy_number: str, data: dict):
    # Mettre à jour la source
    updated = await policy_admin.update(policy_number, data)

    # Invalider le cache
    redis_client.delete(f"policy:{policy_number}")

    # Invalider les caches liés
    redis_client.delete(f"customer:{updated['customer_id']}:policies")

    return updated
```

## Patterns Avancés

### Cache Stampede Protection

Éviter que tous les clients rechargent en même temps.

```python
import asyncio

async def get_with_stampede_protection(key: str, loader, ttl: int = 300):
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    # Acquérir un lock pour ce key
    lock_key = f"lock:{key}"
    acquired = redis_client.setnx(lock_key, "1")

    if acquired:
        redis_client.expire(lock_key, 10)  # Lock de 10 secondes
        try:
            # Charger et cacher
            value = await loader()
            redis_client.setex(key, ttl, json.dumps(value))
            return value
        finally:
            redis_client.delete(lock_key)
    else:
        # Attendre et réessayer
        await asyncio.sleep(0.1)
        return await get_with_stampede_protection(key, loader, ttl)
```

### Cache Multi-Niveau

Combiner cache local et distribué.

```python
class MultiLevelCache:
    def __init__(self):
        self.local = TTLCache(maxsize=100, ttl=60)  # 1 minute
        self.redis = redis.Redis()

    async def get(self, key: str, loader):
        # Niveau 1 : Cache local
        if key in self.local:
            return self.local[key]

        # Niveau 2 : Cache Redis
        cached = self.redis.get(key)
        if cached:
            value = json.loads(cached)
            self.local[key] = value  # Populer le cache local
            return value

        # Niveau 3 : Source
        value = await loader()
        self.local[key] = value
        self.redis.setex(key, 300, json.dumps(value))
        return value
```

## Cas Assurance

### Quoi Cacher ?

| Donnée | TTL | Stratégie |
|--------|-----|-----------|
| Configuration produits | 1h | Cache-aside |
| Tarifs | 15min | TTL avec refresh |
| Infos client | 5min | Write-through |
| Polices | 5min | Cache-aside + invalidation |
| Liste devis | 1min | TTL court |

### Exemple : Cache Tarification

```python
class RatingCache:
    """Cache pour les tarifs du service externe."""

    def __init__(self, redis_client, external_rating):
        self.redis = redis_client
        self.rating_service = external_rating
        self.ttl = 900  # 15 minutes

    async def get_rate(self, product: str, risk_profile: dict) -> dict:
        # Générer une clé stable
        cache_key = f"rate:{product}:{self._hash_profile(risk_profile)}"

        # Vérifier le cache
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Appel au service externe (lent, peut échouer)
        try:
            rate = await self.rating_service.get_rate(product, risk_profile)
            self.redis.setex(cache_key, self.ttl, json.dumps(rate))
            return rate
        except ServiceUnavailable:
            # Fallback: utiliser un cache plus ancien si disponible
            stale = self.redis.get(f"stale:{cache_key}")
            if stale:
                return json.loads(stale)
            raise

    def _hash_profile(self, profile: dict) -> str:
        """Hash stable d'un profil de risque."""
        import hashlib
        return hashlib.md5(
            json.dumps(profile, sort_keys=True).encode()
        ).hexdigest()[:12]
```

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| TTL approprié | Adapter selon la volatilité des données |
| Métriques | Mesurer hit rate, miss rate, latence |
| Éviction | Prévoir l'éviction des données anciennes |
| Warm-up | Préchauffer le cache au démarrage |
| Fallback | Prévoir le cas cache indisponible |
| Serialisation | Format compact (msgpack vs JSON) |

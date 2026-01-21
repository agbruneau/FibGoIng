# API Composition

## Objectif pédagogique

Maîtriser le pattern de composition d'APIs pour créer des vues agrégées.

## Le besoin : Vue 360° Client

En assurance, les données client sont réparties :

```
┌─────────────────────────────────────────────────────┐
│                    Vue 360° Client                  │
├─────────────────────────────────────────────────────┤
│ Infos client    │ Coordonnées, date naissance      │
│ Polices         │ 3 contrats actifs                 │
│ Sinistres       │ 1 en cours, 5 réglés             │
│ Factures        │ 2500€ payés, 350€ en attente     │
│ Documents       │ 15 documents                      │
│ Score risque    │ 42 (Low risk)                    │
└─────────────────────────────────────────────────────┘
```

Ces données viennent de 6 services différents !

## Pattern API Composition

```
         Client
            │
            ▼
    ┌───────────────┐
    │  Compositeur  │
    │   (Agrégateur)│
    └───────┬───────┘
            │
  ┌─────────┼─────────┬─────────┬─────────┐
  │         │         │         │         │
  ▼         ▼         ▼         ▼         ▼
┌─────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌─────┐
│Cust.│ │Policy │ │Claims │ │Billing│ │Docs │
└─────┘ └───────┘ └───────┘ └───────┘ └─────┘
```

## Implémentation

```python
from fastapi import APIRouter
import asyncio

router = APIRouter()

@router.get("/customers/{customer_id}/360")
async def get_customer_360(customer_id: str):
    """Vue 360° complète d'un client."""

    # Appels parallèles pour minimiser la latence
    results = await asyncio.gather(
        customer_hub.get_customer(customer_id),
        policy_admin.list_policies(customer_id),
        claims_mgmt.list_claims(customer_id=customer_id),
        billing.get_outstanding_balance(customer_id),
        document_mgmt.list_documents(entity_id=customer_id),
        external_rating.get_risk_score(customer_id, {}),
        return_exceptions=True  # Continue si un service échoue
    )

    customer, policies, claims, billing_info, docs, risk = results

    return {
        "customer": _extract_customer_info(customer),
        "policies": {
            "active": [p for p in policies if p["status"] == "ACTIVE"],
            "count": len(policies)
        },
        "claims": {
            "open": [c for c in claims if c["status"] == "OPEN"],
            "history_count": len(claims)
        },
        "billing": billing_info,
        "documents_count": len(docs),
        "risk_assessment": risk if not isinstance(risk, Exception) else None
    }

def _extract_customer_info(customer: dict) -> dict:
    """Extrait les infos essentielles du client."""
    return {
        "id": customer["id"],
        "name": customer["name"],
        "email": customer["email"],
        "since": customer.get("created_at", "")[:10]
    }
```

## Gestion des erreurs partielles

### Stratégie : Graceful Degradation

```python
async def get_customer_360_resilient(customer_id: str):
    """Vue 360° avec dégradation gracieuse."""

    response = {
        "customer": None,
        "policies": {"available": False},
        "claims": {"available": False},
        "billing": {"available": False}
    }

    # Client est obligatoire
    try:
        response["customer"] = await customer_hub.get_customer(customer_id)
    except Exception:
        raise HTTPException(404, "Customer not found")

    # Polices : optionnel
    try:
        policies = await policy_admin.list_policies(customer_id)
        response["policies"] = {
            "available": True,
            "data": policies
        }
    except Exception:
        response["policies"] = {
            "available": False,
            "message": "Service temporairement indisponible"
        }

    # ... idem pour les autres services

    return response
```

### Indicateur de fraîcheur

```json
{
  "customer": { ... },
  "policies": {
    "data": [...],
    "fetched_at": "2024-02-01T10:00:00Z",
    "cache_status": "fresh"
  },
  "claims": {
    "data": [...],
    "fetched_at": "2024-02-01T09:55:00Z",
    "cache_status": "stale"
  }
}
```

## Optimisations

### 1. Cache intelligent

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
async def get_customer_cached(customer_id: str):
    return await customer_hub.get_customer(customer_id)

# Invalidation après 5 minutes
```

### 2. Appels conditionnels

```python
async def get_customer_360(customer_id: str, include: List[str] = None):
    """Vue 360° avec sections optionnelles."""

    include = include or ["customer", "policies", "claims", "billing"]

    tasks = {}
    if "customer" in include:
        tasks["customer"] = customer_hub.get_customer(customer_id)
    if "policies" in include:
        tasks["policies"] = policy_admin.list_policies(customer_id)
    # ...

    results = await asyncio.gather(*tasks.values())
    return dict(zip(tasks.keys(), results))
```

### 3. Pagination des sous-ressources

```python
{
    "customer": { ... },
    "policies": {
        "items": [...],  # 3 premières
        "total": 12,
        "has_more": true,
        "next": "/customers/C001/policies?page=2"
    }
}
```

## Considérations de performance

| Approche | Latence | Complexité |
|----------|---------|------------|
| Séquentiel | Σ latences | Basse |
| Parallèle | Max latence | Moyenne |
| Avec cache | ~0 si cached | Haute |
| Avec timeout | Bornée | Haute |

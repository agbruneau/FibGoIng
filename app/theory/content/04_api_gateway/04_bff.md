# Backend For Frontend (BFF)

## Objectif pédagogique

Comprendre le pattern BFF et savoir quand l'appliquer.

## Le problème

Différents clients ont des besoins différents :

```
Mobile App         Web Portal         Broker API
    │                  │                  │
    │                  │                  │
    ▼                  ▼                  ▼
┌─────────────────────────────────────────────┐
│              API Générique                  │
│  (One-size-fits-all)                        │
└─────────────────────────────────────────────┘
```

**Problèmes :**
- Mobile veut des réponses compactes → Over-fetching
- Web veut des données complètes → Under-fetching
- Chaque client fait N appels → Latence mobile

## La solution : BFF

```
Mobile App         Web Portal         Broker API
    │                  │                  │
    ▼                  ▼                  ▼
┌─────────┐       ┌─────────┐       ┌─────────┐
│   BFF   │       │   BFF   │       │   BFF   │
│ Mobile  │       │   Web   │       │ Broker  │
└────┬────┘       └────┬────┘       └────┬────┘
     │                 │                 │
     └────────────┬────┴─────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼───┐  ┌─────▼────┐  ┌────▼────┐
│ Quotes │  │ Policies │  │ Claims  │
└────────┘  └──────────┘  └─────────┘
```

## Responsabilités du BFF

### 1. Agrégation

Un appel BFF = plusieurs appels backend

```python
# BFF Mobile - Vue dashboard
@app.get("/mobile/dashboard")
async def mobile_dashboard(customer_id: str):
    # Agrège 4 services en 1 appel
    customer = await customer_hub.get(customer_id)
    policies = await policy_admin.list(customer_id, limit=3)
    pending_claims = await claims.list(customer_id, status="OPEN")
    balance = await billing.get_balance(customer_id)

    return {
        "customer_name": customer["name"],
        "active_policies": len(policies),
        "open_claims": len(pending_claims),
        "balance_due": balance["amount"]
    }
```

### 2. Transformation / Optimisation

```python
# Backend retourne
{
    "id": "Q001",
    "customer_id": "C001",
    "product": "AUTO",
    "risk_data": { ... },
    "premium": 650.00,
    "premium_monthly": 54.17,
    "premium_quarterly": 162.50,
    "status": "PENDING",
    "valid_until": "2024-03-01T00:00:00",
    "created_at": "2024-02-01T10:00:00",
    "updated_at": "2024-02-01T10:00:00",
    "internal_ref": "REF-12345",
    ...
}

# BFF Mobile retourne (optimisé)
{
    "id": "Q001",
    "premium": "650€/an",
    "status": "En attente",
    "expires_in": "28 jours"
}
```

### 3. Adaptation protocole

- Mobile : REST léger, réponses JSON compactes
- Web : REST complet, WebSocket pour temps réel
- Broker : SOAP legacy / REST moderne

## Exemple complet : BFF Mobile Assurance

```python
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/mobile", tags=["BFF Mobile"])

@router.get("/home")
async def get_home_screen(user_id: str = Depends(get_current_user)):
    """Écran d'accueil mobile - agrège toutes les infos essentielles."""

    # Appels parallèles pour la performance
    customer, policies, claims, invoices = await asyncio.gather(
        customer_service.get(user_id),
        policy_service.list_active(user_id),
        claims_service.list_open(user_id),
        billing_service.get_pending(user_id)
    )

    return {
        "greeting": f"Bonjour {customer['name'].split()[0]}",
        "summary": {
            "policies": len(policies),
            "open_claims": len(claims),
            "amount_due": sum(i["amount"] for i in invoices)
        },
        "quick_actions": [
            {"id": "declare_claim", "label": "Déclarer un sinistre"},
            {"id": "get_attestation", "label": "Mon attestation"},
            {"id": "contact", "label": "Nous contacter"}
        ],
        "alerts": _build_alerts(invoices, claims)
    }

def _build_alerts(invoices, claims):
    alerts = []
    overdue = [i for i in invoices if i["status"] == "OVERDUE"]
    if overdue:
        alerts.append({
            "type": "warning",
            "message": f"{len(overdue)} facture(s) en retard"
        })
    return alerts
```

## BFF vs API Gateway

| Aspect | API Gateway | BFF |
|--------|-------------|-----|
| Responsabilité | Cross-cutting (auth, rate limit) | Logique métier client-spécifique |
| Qui développe | Équipe plateforme | Équipe frontend |
| Combien | 1 par plateforme | 1 par type de client |
| Intelligence | Routing, sécurité | Agrégation, transformation |

## Quand utiliser un BFF ?

**Utiliser si :**
- Clients très différents (mobile, web, IoT)
- Besoins de performance mobile
- Équipes frontend autonomes

**Éviter si :**
- Un seul type de client
- API simple, pas d'agrégation
- Petite équipe

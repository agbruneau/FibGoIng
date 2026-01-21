# Backend For Frontend (BFF)

## Résumé

Le **Backend For Frontend (BFF)** est un pattern où chaque type de client (mobile, web, partenaire) possède son propre backend dédié qui agrège et adapte les données des services internes.

## Problématique

Un portail courtier et une app mobile ont des besoins différents :

**App Mobile :**
- Données minimales (économie de bande passante)
- Format optimisé pour affichage mobile
- Agrégation poussée (moins d'appels)

**Portail Courtier :**
- Données complètes et détaillées
- Format adapté aux tableaux et exports
- Fonctionnalités avancées

**Sans BFF :**
```
Mobile ───┐
          ├──► API Générique ──► Services
Portail ──┘

Problème : L'API générique est soit trop riche pour mobile,
           soit trop pauvre pour le portail.
```

## Solution : Pattern BFF

```
Mobile App  ───► BFF Mobile  ───┬───► Quote Engine
                                ├───► Policy Admin
                                └───► Customer Hub

Portail     ───► BFF Portail ───┬───► Quote Engine
                                ├───► Policy Admin
                                ├───► Claims
                                └───► Billing
```

Chaque BFF :
- Connaît les besoins de son client
- Agrège les données nécessaires
- Formate les réponses de manière optimale

## Exemple Concret : Vue Client

### API Générique (sans BFF)

Le mobile doit faire 4 appels :

```
1. GET /customers/C001           → Infos client
2. GET /policies?customer=C001   → Polices
3. GET /claims?customer=C001     → Sinistres
4. GET /invoices?customer=C001   → Factures
```

### BFF Mobile

Un seul appel optimisé :

```
GET /mobile/dashboard

{
  "customer": {
    "name": "Jean Dupont",
    "avatar_url": "/img/default.png"
  },
  "summary": {
    "active_policies": 2,
    "pending_claims": 1,
    "next_payment": {
      "amount": 125.00,
      "due_date": "2024-02-15"
    }
  },
  "quick_actions": [
    {"action": "declare_claim", "label": "Déclarer un sinistre"},
    {"action": "view_card", "label": "Ma carte verte"}
  ]
}
```

### BFF Portail Courtier

Données complètes et détaillées :

```
GET /broker/customers/C001/full-view

{
  "customer": {
    "id": "C001",
    "name": "Jean Dupont",
    "email": "jean.dupont@email.com",
    "phone": "06 12 34 56 78",
    "address": { ... },
    "created_at": "2020-01-15",
    "risk_score": 45,
    "lifetime_value": 12500.00
  },
  "policies": [
    {
      "number": "POL-2024-0001",
      "product": "AUTO",
      "premium": 850.00,
      "status": "ACTIVE",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "coverages": ["RC", "VOL", "BRIS_GLACE"],
      "claims_history": [ ... ],
      "documents": [ ... ]
    }
  ],
  "claims": [ ... ],
  "invoices": [ ... ],
  "interactions": [ ... ],
  "recommendations": [
    {"type": "CROSS_SELL", "product": "HABITATION", "reason": "No home insurance"}
  ]
}
```

## Implémentation

### Structure de Code

```
app/
├── bff/
│   ├── __init__.py
│   ├── mobile/
│   │   ├── __init__.py
│   │   ├── routes.py      # Endpoints mobile
│   │   └── aggregators.py # Logique d'agrégation
│   └── broker/
│       ├── __init__.py
│       ├── routes.py      # Endpoints courtier
│       └── aggregators.py
```

### Code BFF Mobile

```python
from fastapi import APIRouter

router = APIRouter(prefix="/mobile")

@router.get("/dashboard")
async def get_mobile_dashboard(customer_id: str):
    """Dashboard optimisé pour l'app mobile."""

    # Appels en parallèle pour la performance
    customer, policies, claims, invoices = await asyncio.gather(
        customer_hub.get_customer(customer_id),
        policy_admin.list_policies(customer_id),
        claims_mgmt.list_claims_summary(customer_id),
        billing.get_next_payment(customer_id)
    )

    # Agrégation et formatage mobile
    return {
        "customer": {
            "name": customer["name"],
            "avatar_url": customer.get("avatar_url", "/img/default.png")
        },
        "summary": {
            "active_policies": len([p for p in policies if p["status"] == "ACTIVE"]),
            "pending_claims": len([c for c in claims if c["status"] == "OPEN"]),
            "next_payment": invoices
        }
    }
```

### Code BFF Courtier

```python
router = APIRouter(prefix="/broker")

@router.get("/customers/{customer_id}/full-view")
async def get_broker_customer_view(customer_id: str):
    """Vue complète client pour le portail courtier."""

    # Tous les détails nécessaires
    customer, policies, claims, invoices, interactions = await asyncio.gather(
        customer_hub.get_customer_full(customer_id),
        policy_admin.list_policies_with_history(customer_id),
        claims_mgmt.list_claims_with_documents(customer_id),
        billing.list_all_invoices(customer_id),
        crm.get_interactions(customer_id)
    )

    # Enrichissement avec calculs métier
    risk_score = calculate_risk_score(customer, claims)
    ltv = calculate_lifetime_value(invoices)
    recommendations = generate_recommendations(customer, policies)

    return {
        "customer": {**customer, "risk_score": risk_score, "lifetime_value": ltv},
        "policies": policies,
        "claims": claims,
        "invoices": invoices,
        "interactions": interactions,
        "recommendations": recommendations
    }
```

## BFF vs API Gateway

| Aspect | API Gateway | BFF |
|--------|-------------|-----|
| Rôle | Routing, sécurité | Agrégation, adaptation |
| Logique métier | Non | Oui |
| Un par client | Non | Oui (pattern) |
| Transformation | Légère | Complète |

**Complémentaires :** Gateway devant, BFFs derrière.

```
Client ──► Gateway ──► BFF Mobile  ──► Services
                   └──► BFF Broker ──► Services
```

## Quand Utiliser le BFF ?

### Cas d'usage favorables

- Clients avec besoins très différents
- Besoin d'agrégation de multiples services
- Optimisation réseau importante (mobile)
- Équipes frontend autonomes

### À éviter si

- Un seul type de client
- Services déjà bien adaptés
- Équipe limitée (duplication de code)
- Besoins quasi-identiques entre clients

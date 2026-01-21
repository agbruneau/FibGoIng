# Gestion des Erreurs HTTP

## Résumé

Une bonne gestion des erreurs est essentielle pour une API utilisable. Les clients doivent comprendre ce qui s'est passé et comment corriger le problème.

## Codes de Statut HTTP

### 2xx - Succès

| Code | Nom | Usage |
|------|-----|-------|
| 200 | OK | Requête réussie (GET, PUT, PATCH) |
| 201 | Created | Ressource créée (POST) |
| 202 | Accepted | Traitement asynchrone accepté |
| 204 | No Content | Succès sans contenu (DELETE) |

### 4xx - Erreur Client

| Code | Nom | Usage |
|------|-----|-------|
| 400 | Bad Request | Requête mal formée, données invalides |
| 401 | Unauthorized | Authentification requise |
| 403 | Forbidden | Authentifié mais non autorisé |
| 404 | Not Found | Ressource inexistante |
| 409 | Conflict | Conflit (ex: duplicate) |
| 422 | Unprocessable Entity | Validation métier échouée |
| 429 | Too Many Requests | Rate limiting |

### 5xx - Erreur Serveur

| Code | Nom | Usage |
|------|-----|-------|
| 500 | Internal Server Error | Erreur inattendue |
| 502 | Bad Gateway | Service dépendant indisponible |
| 503 | Service Unavailable | Service temporairement down |
| 504 | Gateway Timeout | Timeout sur service dépendant |

## Structure de Réponse d'Erreur

### Format Standard

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "La requête contient des données invalides",
    "details": [
      {
        "field": "customer_id",
        "message": "Ce champ est requis"
      },
      {
        "field": "premium",
        "message": "Doit être un nombre positif"
      }
    ],
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

### Codes d'Erreur Métier

```json
// 404 - Ressource non trouvée
{
  "error": {
    "code": "QUOTE_NOT_FOUND",
    "message": "Le devis Q001 n'existe pas"
  }
}

// 409 - Conflit métier
{
  "error": {
    "code": "QUOTE_ALREADY_ACCEPTED",
    "message": "Ce devis a déjà été accepté",
    "details": {
      "accepted_at": "2024-01-10T14:30:00Z"
    }
  }
}

// 422 - Règle métier violée
{
  "error": {
    "code": "QUOTE_EXPIRED",
    "message": "Ce devis a expiré le 2024-01-01",
    "details": {
      "expired_at": "2024-01-01T00:00:00Z",
      "action": "Créez un nouveau devis"
    }
  }
}
```

## Erreurs Spécifiques Assurance

### Codes d'Erreur Quote Engine

| Code | HTTP | Description |
|------|------|-------------|
| QUOTE_NOT_FOUND | 404 | Devis inexistant |
| QUOTE_EXPIRED | 422 | Devis expiré |
| QUOTE_ALREADY_ACCEPTED | 409 | Déjà accepté |
| INVALID_PRODUCT | 400 | Produit non supporté |
| RISK_TOO_HIGH | 422 | Risque non assurable |

### Codes d'Erreur Policy Admin

| Code | HTTP | Description |
|------|------|-------------|
| POLICY_NOT_FOUND | 404 | Police inexistante |
| POLICY_NOT_ACTIVE | 422 | Police non active |
| POLICY_ALREADY_CANCELLED | 409 | Déjà résiliée |
| INVALID_COVERAGE | 400 | Garantie invalide |
| PREMIUM_UNPAID | 422 | Prime impayée |

### Codes d'Erreur Claims

| Code | HTTP | Description |
|------|------|-------------|
| CLAIM_NOT_FOUND | 404 | Sinistre inexistant |
| INVALID_TRANSITION | 422 | Transition de statut invalide |
| POLICY_NOT_ACTIVE_AT_DATE | 422 | Police non active à la date du sinistre |
| COVERAGE_NOT_INCLUDED | 422 | Garantie non souscrite |

## Bonnes Pratiques

### 1. Être Spécifique

```json
// ❌ Mauvais
{
  "error": "Error"
}

// ✅ Bon
{
  "error": {
    "code": "INSUFFICIENT_COVERAGE",
    "message": "La garantie VOL n'est pas incluse dans cette police",
    "details": {
      "policy_coverages": ["RC", "BRIS_GLACE"],
      "required_coverage": "VOL"
    }
  }
}
```

### 2. Ne Pas Exposer les Détails Techniques

```json
// ❌ Mauvais (expose l'implémentation)
{
  "error": "SQLException: ORA-00001 unique constraint violated"
}

// ✅ Bon
{
  "error": {
    "code": "DUPLICATE_POLICY",
    "message": "Une police avec ce numéro existe déjà"
  }
}
```

### 3. Fournir des Solutions

```json
{
  "error": {
    "code": "QUOTE_EXPIRED",
    "message": "Ce devis a expiré",
    "resolution": "Créez un nouveau devis avec POST /quotes",
    "_links": {
      "create_quote": {
        "href": "/quotes",
        "method": "POST"
      }
    }
  }
}
```

### 4. Logging et Traçabilité

Toujours inclure un `request_id` pour le support :

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Une erreur inattendue s'est produite",
    "request_id": "req-abc123",
    "support": "Contactez le support avec ce request_id"
  }
}
```

## Implémentation FastAPI

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id
            }
        }
    )

# Usage
raise AppException("QUOTE_NOT_FOUND", "Devis Q001 non trouvé", 404)
```

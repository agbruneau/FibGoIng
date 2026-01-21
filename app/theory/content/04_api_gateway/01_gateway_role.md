# Rôle de l'API Gateway

## Objectif pédagogique

Comprendre le rôle central de l'API Gateway dans une architecture d'intégration.

## Qu'est-ce qu'une API Gateway ?

Une API Gateway est un point d'entrée unique qui se place devant vos APIs pour :

```
┌─────────────────────────────────────────────────────────┐
│                      Clients                            │
│   (Mobile App, Web Portal, Courtier, Partenaire)        │
└───────────────────────────┬─────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │  API Gateway  │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐        ┌─────▼─────┐       ┌────▼────┐
   │ Quote   │        │  Policy   │       │ Claims  │
   │ Engine  │        │  Admin    │       │ System  │
   └─────────┘        └───────────┘       └─────────┘
```

## Responsabilités principales

### 1. Routage

Diriger les requêtes vers le bon service backend :

```yaml
routes:
  - path: /quotes/**
    service: quote-engine
  - path: /policies/**
    service: policy-admin
  - path: /claims/**
    service: claims-management
```

### 2. Authentification et Autorisation

```
Client → Gateway → Vérifie JWT → Autorise → Backend
```

- Validation des tokens JWT
- Vérification des scopes/permissions
- Propagation de l'identité

### 3. Rate Limiting

Protection contre la surcharge :

```yaml
rate_limits:
  - path: /quotes
    limit: 100 requests/minute/client
  - path: /claims
    limit: 50 requests/minute/client
```

### 4. Transformation

Adapter les requêtes/réponses :

```
Client v2 → Gateway (transforme) → Backend v1
```

### 5. Monitoring et Logging

- Métriques (latence, erreurs, volume)
- Traces distribuées
- Logs centralisés

## Avantages

| Aspect | Sans Gateway | Avec Gateway |
|--------|--------------|--------------|
| Sécurité | Chaque service gère l'auth | Centralisée |
| Évolutivité | Clients couplés aux services | Découplage |
| Monitoring | Dispersé | Unifié |
| Versioning | Complexe | Simplifié |

## Dans l'écosystème assurance

### Exemple concret

```
Mobile App Assuré
    │
    ▼
┌──────────────────────────────┐
│        API Gateway           │
│  - Auth JWT                  │
│  - Rate limit: 100/min       │
│  - Route vers BFF Mobile     │
└──────────────┬───────────────┘
               │
        ┌──────▼──────┐
        │ BFF Mobile  │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌───▼───┐  ┌───▼───┐
│Quotes │  │Policy │  │Claims │
└───────┘  └───────┘  └───────┘
```

## Quiz

1. **Pourquoi centraliser l'authentification dans la Gateway ?**
   - Évite la duplication de code
   - Point de contrôle unique
   - Facilite les audits de sécurité

2. **Le rate limiting protège contre quoi ?**
   - Attaques DDoS
   - Clients mal configurés (boucles)
   - Surconsommation de ressources

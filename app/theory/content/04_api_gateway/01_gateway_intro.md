# Introduction aux API Gateways

## Résumé

Un **API Gateway** est un point d'entrée unique pour tous les clients d'un système. Il agit comme un reverse proxy qui route les requêtes vers les services appropriés tout en fournissant des fonctionnalités transversales.

## Problématique

Dans un écosystème d'assurance avec de nombreux services :
- Quote Engine, Policy Admin, Claims, Billing, etc.
- Chaque service a sa propre URL
- Différents clients : App mobile, Portail courtier, Partenaires

**Sans Gateway :**

```
Mobile App  ───┬───► Quote Engine
               ├───► Policy Admin
               ├───► Claims
               └───► Billing

Portail     ───┬───► Quote Engine
               ├───► Policy Admin
               └───► Claims

Partenaire  ───┬───► Quote Engine
               └───► Policy Admin
```

**Problèmes :**
- Chaque client doit connaître toutes les URLs
- Authentification dupliquée dans chaque service
- Pas de vision centralisée du trafic
- Changement d'URL = impact sur tous les clients

## Solution : API Gateway

```
Mobile App  ───┐
               │
Portail     ───┼───► API Gateway ───┬───► Quote Engine
               │                    ├───► Policy Admin
Partenaire  ───┘                    ├───► Claims
                                    └───► Billing
```

## Fonctionnalités d'un Gateway

### 1. Routing

Dirige les requêtes vers le bon service backend.

```yaml
routes:
  - path: /quotes/**
    service: quote-engine

  - path: /policies/**
    service: policy-admin

  - path: /claims/**
    service: claims-management
```

### 2. Load Balancing

Distribue la charge entre plusieurs instances.

```
/quotes ──► Gateway ──┬──► Quote Engine #1
                      ├──► Quote Engine #2
                      └──► Quote Engine #3
```

### 3. Authentification

Vérifie l'identité du client une seule fois.

```
Client ──► Gateway [Vérifie JWT] ──► Services [déjà authentifié]
```

### 4. Rate Limiting

Limite le nombre de requêtes par client.

```
Partenaire A : 1000 req/min
Partenaire B : 5000 req/min
Mobile App   : 100 req/min/user
```

### 5. Transformation

Adapte les requêtes/réponses.

```
Client: GET /v1/quotes/123
Gateway: GET /internal/quotes/123 (version différente)
```

### 6. Monitoring

Collecte des métriques sur tout le trafic.

```
- Nombre de requêtes
- Latence par endpoint
- Taux d'erreur
- Distribution par client
```

## Architecture dans l'Assurance

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                           │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │  Auth    │ Rate     │ Logging  │ Circuit Breaker │  │
│  │          │ Limit    │          │                 │  │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
│                                                         │
│  Routing Rules:                                         │
│  /partners/** → Rate limit 5000/min + API Key auth     │
│  /mobile/**   → Rate limit 100/min/user + JWT auth      │
│  /internal/** → mTLS required                           │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Quote Engine │   │ Policy Admin │   │    Claims    │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Solutions Techniques

| Solution | Type | Usage |
|----------|------|-------|
| Kong | Open Source | Enterprise, extensible |
| AWS API Gateway | Cloud | Serverless, AWS natif |
| Azure API Management | Cloud | Azure natif |
| Nginx | Open Source | Léger, performant |
| Envoy | Open Source | Service mesh, Kubernetes |
| Traefik | Open Source | Kubernetes, auto-discovery |

## Avantages / Inconvénients

### Avantages

- **Point unique** d'entrée et de configuration
- **Sécurité centralisée** (auth, rate limiting)
- **Observabilité** complète du trafic
- **Découplage** clients/services

### Inconvénients

- **SPOF** (Single Point of Failure) si mal configuré
- **Latence additionnelle** (un hop supplémentaire)
- **Complexité** de configuration
- **Point de congestion** possible

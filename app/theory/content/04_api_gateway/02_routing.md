# Routing et Load Balancing

## Objectif pédagogique

Maîtriser les stratégies de routage et de répartition de charge.

## Routage basique

### Par chemin (Path-based)

```yaml
routes:
  - match:
      path_prefix: /api/v1/quotes
    route:
      cluster: quote-engine-cluster

  - match:
      path_prefix: /api/v1/policies
    route:
      cluster: policy-admin-cluster

  - match:
      path_prefix: /api/v1/claims
    route:
      cluster: claims-cluster
```

### Par header

```yaml
routes:
  - match:
      headers:
        X-Channel: mobile
    route:
      cluster: bff-mobile

  - match:
      headers:
        X-Channel: broker
    route:
      cluster: bff-broker
```

### Par méthode HTTP

```yaml
routes:
  - match:
      path: /quotes
      methods: [GET]
    route:
      cluster: quote-read-cluster

  - match:
      path: /quotes
      methods: [POST]
    route:
      cluster: quote-write-cluster
```

## Load Balancing

### Stratégies courantes

#### Round Robin
```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A
...
```

#### Weighted Round Robin
```yaml
cluster:
  endpoints:
    - address: server-a
      weight: 60  # 60% du trafic
    - address: server-b
      weight: 40  # 40% du trafic
```

#### Least Connections
Envoie vers le serveur avec le moins de connexions actives.

#### IP Hash / Session Affinity
Même client → même serveur (utile pour le cache local).

## Health Checks

### Active Health Check

```yaml
health_check:
  path: /health
  interval: 10s
  timeout: 2s
  healthy_threshold: 2
  unhealthy_threshold: 3
```

### Passive Health Check

Observe les réponses réelles :
- 5 erreurs 5xx consécutives → serveur marqué "unhealthy"
- Attente avant réintégration

## Circuit Breaker

Protection contre les cascades d'erreurs :

```
┌─────────┐      ┌─────────┐      ┌─────────┐
│ CLOSED  │ ───▶ │  OPEN   │ ───▶ │HALF-OPEN│
│(normal) │      │(échecs) │      │ (test)  │
└─────────┘      └─────────┘      └─────────┘
     ▲                                  │
     └──────────────────────────────────┘
                 (succès)
```

```yaml
circuit_breaker:
  max_connections: 100
  max_pending_requests: 50
  max_requests: 1000
  consecutive_5xx: 5
  interval: 30s
```

## Exemple pratique : Multi-partenaires

```yaml
# Routage par partenaire (header X-Partner-ID)
routes:
  - match:
      headers:
        X-Partner-ID: PARTNER-A
    route:
      cluster: partner-a-cluster
      rate_limit: 1000/min

  - match:
      headers:
        X-Partner-ID: PARTNER-B
    route:
      cluster: partner-b-cluster
      rate_limit: 500/min

  - default:
      route:
        cluster: public-cluster
        rate_limit: 100/min
```

# CLAUDE.md - Guide de Développement pour IA

Ce fichier documente l'architecture, les patterns et les leçons apprises du projet **kafka-eda-lab**. Les futures IA doivent lire ce fichier intégralement avant toute modification du code.

---

## Table des Matières

1. [Leçons Critiques](#1-leçons-critiques)
2. [Architecture du Projet](#2-architecture-du-projet)
3. [Patterns Kafka](#3-patterns-kafka)
4. [Patterns Base de Données](#4-patterns-base-de-données)
5. [Conventions API REST](#5-conventions-api-rest)
6. [Conventions de Code Go](#6-conventions-de-code-go)
7. [Configuration et Environnement](#7-configuration-et-environnement)
8. [Infrastructure Docker](#8-infrastructure-docker)
9. [Référence Rapide des Fichiers](#9-référence-rapide-des-fichiers)

---

## 1. Leçons Critiques

### 1.1 Routage HTTP avec `http.ServeMux`

**Problème** : Dashboard retournait 404 malgré un démarrage correct du serveur.

**Cause** : Utilisation incorrecte de préfixes de méthode HTTP avec `http.ServeMux` standard.

```go
// ❌ INCORRECT - Provoque 404 (Go < 1.22)
mux.HandleFunc("GET /", handler)
mux.HandleFunc("GET /events", handler)

// ✅ CORRECT - Fonctionne avec http.ServeMux
mux.HandleFunc("/", handler)
mux.HandleFunc("/events", handler)
```

**Règle** : Vérifier `go.mod` avant d'utiliser des patterns avec méthodes. Ce projet utilise **Go 1.21** → pas de préfixes de méthode.

| Version Go | Pattern supporté |
|------------|------------------|
| < 1.22 | `mux.HandleFunc("/path", h)` uniquement |
| ≥ 1.22 | `mux.HandleFunc("GET /path", h)` supporté |

### 1.2 CGO et SQLite sur Windows

**Problème** : Services compilés mais échec à l'exécution avec erreur CGO.

```
Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work
```

**Cause** : `go-sqlite3` nécessite un compilateur C (GCC/MinGW).

**Solutions** :
1. **Docker** (recommandé) : Utiliser `Dockerfile.services` avec `CGO_ENABLED=1`
2. **Windows natif** : Installer MSYS2/MinGW-w64, ajouter au PATH

### 1.3 Sarama et Configuration Kafka

**Attention** : La bibliothèque Sarama requiert une configuration précise.

```go
// Configuration minimale obligatoire
config.Producer.Return.Successes = true  // Pour SyncProducer
config.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{
    sarama.NewBalanceStrategyRoundRobin(),
}
```

---

## 2. Architecture du Projet

### 2.1 Vue d'Ensemble

```
kafka-eda-lab/
├── cmd/                    # Points d'entrée des services
│   ├── dashboard/          # UI web (port 8080)
│   ├── quotation/          # Service devis (port 8081)
│   ├── souscription/       # Service contrats (port 8082)
│   ├── reclamation/        # Service sinistres (port 8083)
│   └── simulator/          # Générateur de charge
├── internal/               # Packages privés
│   ├── database/           # Couche données (Repository pattern)
│   ├── kafka/              # Producteur/Consommateur Kafka
│   ├── models/             # Modèles domaine et événements
│   └── services/           # Logique métier par domaine
├── docker/                 # Configuration observabilité
│   ├── grafana/            # Dashboards Grafana
│   ├── prometheus/         # Configuration Prometheus
│   └── loki/               # Configuration Loki
└── tests/                  # Tests integration/charge
```

### 2.2 Flux de Données

```
┌─────────────┐     HTTP      ┌─────────────┐
│  Simulator  │──────────────▶│  Quotation  │
└─────────────┘               └──────┬──────┘
                                     │ Kafka: devis-genere
                                     ▼
                              ┌─────────────┐
                              │Souscription │
                              └──────┬──────┘
                                     │ Kafka: contrat-emis
                                     ▼
                              ┌─────────────┐
                              │ Reclamation │
                              └─────────────┘
```

### 2.3 Principes Architecturaux

1. **Base de données par service** : Chaque microservice possède sa propre base SQLite
2. **Communication asynchrone** : Services découplés via Kafka
3. **Consistance éventuelle** : Pas de transactions distribuées
4. **Idempotence** : Les handlers d'événements doivent être idempotents

---

## 3. Patterns Kafka

### 3.1 Convention de Nommage des Topics

```
{service}.{nom-evenement}

Exemples:
- quotation.devis-genere
- quotation.devis-expire
- souscription.contrat-emis
- souscription.contrat-modifie
- souscription.contrat-resilie
- reclamation.sinistre-declare
- reclamation.sinistre-evalue
- reclamation.indemnisation-effectuee
```

### 3.2 Structure des Événements

Tous les événements suivent cette enveloppe :

```go
type Event struct {
    ID        string      `json:"id"`        // UUID v4
    Type      string      `json:"type"`      // Nom de l'événement
    Source    string      `json:"source"`    // Service émetteur
    Timestamp time.Time   `json:"timestamp"` // UTC
    Data      interface{} `json:"data"`      // Payload spécifique
}
```

### 3.3 Producteur Kafka

```go
// Envoi synchrone (opérations critiques)
err := producer.Send(ctx, &kafka.Message{
    Topic: models.TopicDevisGenere,
    Key:   []byte(devis.ID),
    Value: jsonData,
})

// Envoi asynchrone (notifications)
producer.SendAsync(&kafka.Message{...})

// Envoi avec enveloppe Event (recommandé)
producer.SendEvent(ctx, topic, eventType, source, data)
```

### 3.4 Consommateur Kafka

```go
// Enregistrer un handler par topic
consumer.RegisterHandler(models.TopicDevisGenere, func(ctx context.Context, msg *kafka.ReceivedMessage) error {
    var event models.DevisGenere
    if err := json.Unmarshal(msg.Value, &event); err != nil {
        return err
    }
    // Traitement...
    return nil
})

// Démarrer la consommation
consumer.Start(ctx, []string{models.TopicDevisGenere, models.TopicDevisExpire})
```

### 3.5 Configuration Kafka

| Variable | Défaut | Description |
|----------|--------|-------------|
| `KAFKA_BROKERS` | `localhost:9092` | Liste des brokers |
| `KAFKA_CLIENT_ID` | `kafka-eda-lab` | Identifiant client |
| `KAFKA_GROUP_ID` | `{service}-group` | Consumer group |

---

## 4. Patterns Base de Données

### 4.1 Repository Pattern

Chaque entité a une interface et une implémentation SQLite :

```go
// Interface (internal/database/quotation_repository.go)
type QuotationRepository interface {
    Create(ctx context.Context, devis *models.Devis) error
    GetByID(ctx context.Context, id string) (*models.Devis, error)
    GetByClientID(ctx context.Context, clientID string) ([]*models.Devis, error)
    UpdateStatus(ctx context.Context, id string, status models.StatutDevis) error
    List(ctx context.Context, limit, offset int) ([]*models.Devis, error)
    Count(ctx context.Context) (int, error)
}

// Implémentation
type SQLiteQuotationRepository struct {
    db *DB
}
```

### 4.2 Schéma de Base

```sql
-- Table devis (quotation)
CREATE TABLE devis (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    type_bien TEXT CHECK(type_bien IN ('AUTO','HABITATION','AUTRE')),
    valeur REAL NOT NULL,
    prime REAL NOT NULL,
    statut TEXT DEFAULT 'GENERE',
    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
    date_expiration DATETIME NOT NULL
);

-- Table contrats (souscription)
CREATE TABLE contrats (
    id TEXT PRIMARY KEY,
    devis_id TEXT REFERENCES devis(id),
    client_id TEXT NOT NULL,
    -- ... autres champs
);

-- Table sinistres (reclamation)
CREATE TABLE sinistres (
    id TEXT PRIMARY KEY,
    contrat_id TEXT REFERENCES contrats(id),
    -- ... autres champs
);
```

### 4.3 Gestion des Champs Nullables

```go
// Utiliser sql.NullTime pour les dates optionnelles
var dateFin sql.NullTime
row.Scan(&dateFin)

if dateFin.Valid {
    contrat.DateFin = &dateFin.Time
}

// Utiliser des pointeurs dans les modèles
type Contrat struct {
    DateFin *time.Time `json:"dateFin,omitempty"`
}
```

---

## 5. Conventions API REST

### 5.1 Structure des Routes

```
POST   /api/v1/{ressource}           → Créer
GET    /api/v1/{ressource}           → Lister (avec pagination)
GET    /api/v1/{ressource}/{id}      → Obtenir un élément
PUT    /api/v1/{ressource}/{id}      → Modifier
DELETE /api/v1/{ressource}/{id}      → Supprimer
GET    /api/v1/{service}/health      → Health check
GET    /api/v1/{service}/stats       → Statistiques
```

### 5.2 Format de Réponse Standard

```go
type Response struct {
    Success bool        `json:"success"`
    Data    interface{} `json:"data,omitempty"`
    Error   string      `json:"error,omitempty"`
}

// Succès
{"success": true, "data": {...}}

// Erreur
{"success": false, "error": "description de l'erreur"}
```

### 5.3 Codes HTTP

| Code | Utilisation |
|------|-------------|
| 200 | GET/PUT réussi |
| 201 | POST créé avec succès |
| 400 | Requête invalide (validation) |
| 404 | Ressource non trouvée |
| 500 | Erreur serveur |

### 5.4 Pagination

```go
// Query params: ?limit=50&offset=0
limit := 50  // défaut, max 100
offset := 0  // défaut

// Parsing
if l := r.URL.Query().Get("limit"); l != "" {
    limit, _ = strconv.Atoi(l)
    if limit > 100 { limit = 100 }
}
```

### 5.5 Middleware Chain

```go
// Ordre: CORS → Logging → Handler
server := &http.Server{
    Handler: corsMiddleware(loggingMiddleware(mux)),
}
```

---

## 6. Conventions de Code Go

### 6.1 Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Types exportés | PascalCase | `QuotationService` |
| Méthodes | PascalCase | `CreateDevis()` |
| Variables | camelCase | `clientID` |
| Constantes | PascalCase | `TopicDevisGenere` |
| Packages | lowercase | `quotation`, `kafka` |
| Termes domaine | Français | `devis`, `contrat`, `sinistre` |

### 6.2 Gestion des Erreurs

```go
// Wrapping avec contexte
if err != nil {
    return fmt.Errorf("création devis échouée: %w", err)
}

// Logging des erreurs inattendues
log.Printf("[Service] Erreur: %v", err)

// Ne jamais panic, toujours retourner error
```

### 6.3 Logging

```go
// Préfixe par composant
log.Printf("[Quotation] Devis créé: %s", devis.ID)
log.Printf("[HTTP] %s %s - %v", r.Method, r.URL.Path, duration)
log.Printf("[Kafka] Message envoyé sur %s", topic)
```

### 6.4 Lifecycle des Services

```go
type Service struct {
    stopChan chan struct{}
    wg       sync.WaitGroup
}

func (s *Service) Start(ctx context.Context) {
    s.wg.Add(1)
    go func() {
        defer s.wg.Done()
        // Boucle de traitement
        for {
            select {
            case <-s.stopChan:
                return
            case <-time.After(interval):
                s.process()
            }
        }
    }()
}

func (s *Service) Stop() {
    close(s.stopChan)
    s.wg.Wait()
}
```

### 6.5 Constructeurs

```go
// Utiliser New* pour les constructeurs
func NewService(repo Repository, producer *kafka.Producer) *Service {
    return &Service{
        repo:     repo,
        producer: producer,
        stopChan: make(chan struct{}),
    }
}
```

---

## 7. Configuration et Environnement

### 7.1 Variables d'Environnement

| Variable | Service | Défaut | Description |
|----------|---------|--------|-------------|
| `HTTP_PORT` | Tous | 8080-8083 | Port HTTP |
| `DB_PATH` | Métier | `data/{svc}.db` | Chemin SQLite |
| `KAFKA_BROKERS` | Tous | `localhost:9092` | Brokers Kafka |
| `SCHEMA_REGISTRY_URL` | Tous | `http://localhost:8081` | Schema Registry |
| `SIMULATION_RATE` | Simulator | `1.0` | Événements/seconde |

### 7.2 Pattern de Configuration

```go
func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}

// Usage
httpPort := getEnv("HTTP_PORT", "8081")
```

---

## 8. Infrastructure Docker

### 8.1 Services Infrastructure (docker-compose.yml)

| Service | Port | Description |
|---------|------|-------------|
| kafka | 9092 | Broker Kafka (KRaft) |
| schema-registry | 8081 | Confluent Schema Registry |
| kafka-ui | 8090 | Interface web Kafka |
| prometheus | 9090 | Métriques |
| grafana | 3000 | Dashboards (admin/admin) |
| loki | 3100 | Agrégation de logs |
| jaeger | 16686 | Tracing distribué |

### 8.2 Services Applicatifs (docker-compose.services.yml)

```bash
# Infrastructure seule
docker compose up -d

# Infrastructure + Services
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d

# Avec simulateur
docker compose -f docker-compose.yml -f docker-compose.services.yml --profile simulation up -d
```

### 8.3 Build Multi-Stage (Dockerfile.services)

```dockerfile
# Build avec CGO
FROM golang:1.21-alpine AS builder
RUN apk add --no-cache gcc musl-dev
ENV CGO_ENABLED=1
RUN go build -o /bin/quotation ./cmd/quotation

# Runtime minimal
FROM alpine:3.19 AS quotation
COPY --from=builder /bin/quotation /bin/quotation
CMD ["/bin/quotation"]
```

---

## 9. Référence Rapide des Fichiers

### 9.1 Points d'Entrée

| Fichier | Port | Rôle |
|---------|------|------|
| `cmd/dashboard/main.go` | 8080 | UI web + SSE |
| `cmd/quotation/main.go` | 8081 | Service devis |
| `cmd/souscription/main.go` | 8082 | Service contrats |
| `cmd/reclamation/main.go` | 8083 | Service sinistres |
| `cmd/simulator/main.go` | - | Générateur charge |

### 9.2 Packages Internes

| Package | Fichiers Clés | Responsabilité |
|---------|---------------|----------------|
| `internal/kafka` | `config.go`, `producer.go`, `consumer.go` | Abstraction Kafka |
| `internal/database` | `sqlite.go`, `*_repository.go` | Accès données |
| `internal/models` | `quotation.go`, `contrat.go`, `sinistre.go`, `events.go` | Modèles domaine |
| `internal/services/*` | `service.go`, `handlers.go`, `metrics.go` | Logique métier |

### 9.3 Configuration Docker

| Fichier | Usage |
|---------|-------|
| `docker-compose.yml` | Infrastructure (Kafka, monitoring) |
| `docker-compose.services.yml` | Services applicatifs |
| `Dockerfile.services` | Build multi-stage des services |

---

## Checklist avant Modification

- [ ] Vérifier la version Go dans `go.mod` (actuellement 1.21)
- [ ] Utiliser les patterns existants (Repository, Event envelope)
- [ ] Respecter les conventions de nommage (français pour le domaine)
- [ ] Ajouter les métriques Prometheus si nouveau endpoint
- [ ] Tester avec `go build ./...` avant de valider
- [ ] Documenter les nouvelles variables d'environnement

---

*Dernière mise à jour : Janvier 2026*

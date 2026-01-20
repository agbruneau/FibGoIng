# PLAN.MD - Plan d'implémentation EDA-Lab

## Vue d'ensemble

Ce document définit le plan d'implémentation du projet **EDA-Lab** selon une approche **Test Driven Development (TDD)** avec progression incrémentale.

**Principes directeurs :**
- Chaque étape produit du code fonctionnel et testé
- Tests avec données réelles (testcontainers-go)
- Aucun code orphelin - intégration continue
- Progression sans sauts de complexité

---

## Relation avec PRD.MD

| Document | Contenu |
|----------|---------|
| **PRD.MD** | QUOI construire (événements, domaines, architecture) |
| **PLAN.MD** | COMMENT construire (phases techniques, prompts Claude Code) |

> L'**Itération 1 (MVP Pub/Sub)** du PRD.MD est construite via les **Phases 0-8** de ce document.

---

## Structure des phases

| Phase | Nom | Objectif |
|-------|-----|----------|
| 0 | Infrastructure | Docker Compose, Kafka, PostgreSQL, Schema Registry |
| 1 | Fondations Go | Structure monorepo, bibliothèques partagées |
| 2 | Schémas Avro | Définition et enregistrement des schémas |
| 3 | Producteur | Service Simulator - génération d'événements |
| 4 | Consommateur | Service Bancaire - consommation et traitement |
| 5 | Gateway | API REST + WebSocket |
| 6 | Observabilité | Prometheus, Grafana, métriques |
| 7 | Web UI | Interface React + React Flow |
| 8 | Intégration | Tests E2E, scénarios complets |

---

## Convention TDD

Chaque sous-étape suit le cycle :

```
1. RED    : Écrire le test qui échoue
2. GREEN  : Implémenter le minimum pour passer
3. REFACTOR : Améliorer sans changer le comportement
```

---

## Convention CHECKPOINT

Chaque phase se termine par un checkpoint avec :
- Commandes de validation à exécuter
- Checklist des critères
- Procédure en cas d'échec

**Ne jamais passer à la phase suivante sans valider le checkpoint.**

---

# PHASE 0 : Infrastructure

## Objectif

Mettre en place l'infrastructure Docker Compose avec Kafka (KRaft), Schema Registry et PostgreSQL.

---

### Étape 0.1 : Structure du projet

#### 0.1.1 : Création de la structure de répertoires

```text
PROMPT CLAUDE CODE

Crée la structure de répertoires pour EDA-Lab selon PRD.MD section 10.

Inclure :
- services/ (bancaire, simulator, gateway)
- schemas/bancaire/
- pkg/ (config, kafka, database, events, observability)
- infra/, scripts/, tests/, web-ui/, scenarios/
- .gitignore (Go, Node.js, Docker)
- go.work avec tous les modules
- README.md minimal

Ne pas créer de code source - uniquement la structure.
```

---

#### 0.1.2 : Docker Compose - Kafka KRaft

```text
PROMPT CLAUDE CODE

Crée infra/docker-compose.yml avec Kafka en mode KRaft.

Spécifications :
- Image : confluentinc/cp-kafka:7.5.0
- Mode KRaft (KAFKA_KRAFT_CLUSTER_ID)
- Ports : 9092 (externe), 29092 (interne)
- Volume persistant
- Healthcheck

Crée scripts/wait-for-kafka.sh pour attendre la disponibilité.
Teste que le conteneur démarre en healthy.
```

---

#### 0.1.3 : Docker Compose - Schema Registry

```text
PROMPT CLAUDE CODE

Ajoute Schema Registry à docker-compose.yml.

Spécifications :
- Image : confluentinc/cp-schema-registry:7.5.0
- Port : 8081
- Connecté à Kafka
- Healthcheck

Crée scripts/test-schema-registry.sh qui :
1. Attend Schema Registry
2. Enregistre un schéma de test
3. Vérifie l'enregistrement

Schéma de test : voir PRD.MD section 5.2 pour le namespace.
```

---

#### 0.1.4 : Docker Compose - PostgreSQL

```text
PROMPT CLAUDE CODE

Ajoute PostgreSQL à docker-compose.yml.

Spécifications :
- Image : postgres:16-alpine
- Port : 5432
- Database : edalab
- User : edalab / edalab_password
- Volume persistant
- Healthcheck

Crée infra/postgres/init.sql :
- Schéma 'bancaire'
- Table health_check

Crée scripts/test-postgres.sh pour valider.
```

---

#### 0.1.5 : Makefile

```text
PROMPT CLAUDE CODE

Crée un Makefile avec les targets :

# Infrastructure
infra-up, infra-down, infra-logs, infra-clean

# Tests
test-infra, test-unit, test-integration, test-e2e

# Kafka
kafka-topics, kafka-create-topic TOPIC=<name>

# Utilitaires
clean, help

Crée scripts/create-topics.sh avec les topics du PRD.MD section 4.
```

---

### Étape 0.2 : Validation infrastructure

#### 0.2.1 : Test d'intégration Go

```text
PROMPT CLAUDE CODE

Crée tests/integration/infrastructure_test.go

Tests (avec infra Docker Compose réelle) :
1. TestKafkaConnection : produce/consume un message
2. TestSchemaRegistryConnection : register/get schema
3. TestPostgreSQLConnection : query simple

Module : github.com/edalab/tests/integration
Dépendances : kafka-go, srclient, pgx/v5, testify
```

---

## CHECKPOINT PHASE 0

```bash
make infra-up && make test-infra
```

**Checklist :**
- [ ] Kafka, Schema Registry, PostgreSQL healthy
- [ ] Topics créés (make kafka-topics)
- [ ] Tests Go passent

---

# PHASE 1 : Fondations Go

## Objectif

Créer les bibliothèques partagées Go (pkg/*).

---

### Étape 1.1 : pkg/config

#### 1.1.1 : Configuration (TDD)

```text
PROMPT CLAUDE CODE - RED

Crée pkg/config/config_test.go avec tests :
1. TestLoadFromEnv_Success
2. TestLoadFromEnv_MissingRequired
3. TestValidate_ValidConfig
4. TestValidate_InvalidConfig

Crée pkg/config/config.go avec structs vides.
Les tests DOIVENT échouer.
```

```text
PROMPT CLAUDE CODE - GREEN

Implémente pkg/config/config.go :
- Structs : KafkaConfig, SchemaConfig, PostgresConfig, ServiceConfig
- LoadFromEnv() avec os.Getenv
- Validate() pour champs obligatoires

Tous les tests doivent passer.
```

---

#### 1.1.2 : Fichiers YAML

```text
PROMPT CLAUDE CODE

Crée config/local.yaml et config/docker.yaml.
Valeurs selon PRD.MD section 5 (ports, hosts).

Ajoute LoadFromFile() à config.go avec gopkg.in/yaml.v3.
```

---

### Étape 1.2 : pkg/kafka

#### 1.2.1 : Producer Avro (TDD)

```text
PROMPT CLAUDE CODE - RED

Crée pkg/kafka/producer_test.go :
1. TestNewAvroProducer_InvalidConfig
2. TestProduce_Interface

Crée pkg/kafka/producer.go avec interface et structs vides.
```

```text
PROMPT CLAUDE CODE - GREEN

Implémente Producer Avro :
- NewAvroProducer : connexion Kafka + Schema Registry
- Produce : serialize Avro, produce, flush

Dépendances : kafka-go, srclient, hamba/avro/v2
```

---

#### 1.2.2 : Consumer Avro (TDD)

```text
PROMPT CLAUDE CODE - RED

Crée pkg/kafka/consumer_test.go :
1. TestNewAvroConsumer_InvalidConfig
2. TestConsume_Interface

Structs et interfaces vides dans consumer.go.
```

```text
PROMPT CLAUDE CODE - GREEN

Implémente Consumer Avro :
- Subscribe(topics)
- Consume(ctx, handler) : poll, deserialize, call handler, commit
```

---

#### 1.2.3 : Test d'intégration Producer-Consumer

```text
PROMPT CLAUDE CODE

Crée pkg/kafka/integration_test.go (build tag: integration)

TestProducerConsumerRoundTrip :
- Producer envoie 10 messages
- Consumer reçoit 10 messages
- Vérifier contenu identique

Utilise infrastructure Docker Compose.
```

---

### Étape 1.3 : pkg/database

#### 1.3.1 : Pool PostgreSQL (TDD)

```text
PROMPT CLAUDE CODE - RED

Crée pkg/database/pool_test.go :
1. TestNewDBPool_InvalidConfig
2. TestHealthCheck_Fail

Structs vides dans pool.go.
```

```text
PROMPT CLAUDE CODE - GREEN

Implémente avec pgxpool :
- NewDBPool : connexion pool
- HealthCheck : ping
- WithTransaction : helper transactions

Tests d'intégration avec vraie DB.
```

---

### Étape 1.4 : pkg/observability

#### 1.4.1 : Métriques Prometheus (TDD)

```text
PROMPT CLAUDE CODE

Crée pkg/observability/metrics.go :
- Vecteurs Prometheus (CounterVec, HistogramVec)
- RegisterMetrics()
- NewMetricsServer() exposant /metrics

Tests : vérifier que /metrics retourne des données.
```

---

#### 1.4.2 : Tracing OpenTelemetry (TDD)

```text
PROMPT CLAUDE CODE

Crée pkg/observability/tracing.go :
- InitTracer (Jaeger exporter)
- StartSpan
- InjectTraceContext / ExtractTraceContext

Tests : round-trip du TraceID.
```

---

#### 1.4.3 : Logging structuré (TDD)

```text
PROMPT CLAUDE CODE

Crée pkg/observability/logging.go :
- InitLogger avec slog.NewJSONHandler
- WithTraceID : enrichir logs avec trace context

Tests : vérifier format JSON et présence trace_id.
```

---

## CHECKPOINT PHASE 1

```bash
go test ./pkg/config/...
go test ./pkg/kafka/...
go test ./pkg/database/...
go test ./pkg/observability/...
go test ./pkg/kafka/... -tags=integration
```

**Checklist :**
- [ ] Tous les packages compilent
- [ ] Tests unitaires passent
- [ ] Tests d'intégration Kafka passent
- [ ] go.work configure le workspace

---

# PHASE 2 : Schémas Avro

## Objectif

Définir et enregistrer les schémas Avro pour le domaine Bancaire.

---

### Étape 2.1 : Schémas du domaine Bancaire

#### 2.1.1 : Schéma CompteOuvert

```text
PROMPT CLAUDE CODE

Crée schemas/bancaire/compte-ouvert.avsc

Champs (voir PRD.MD section 4.1) :
- event_id (string UUID)
- timestamp (timestamp-millis)
- compte_id, client_id (string)
- type_compte (enum: COURANT, EPARGNE, JOINT)
- devise (string, default EUR)
- solde_initial (decimal 18,2)
- metadata (optional map)

Namespace : com.edalab.bancaire.events

Crée scripts/register-schemas.sh pour l'enregistrement.
```

---

#### 2.1.2 : Schémas DepotEffectue et VirementEmis

```text
PROMPT CLAUDE CODE

Crée schemas/bancaire/depot-effectue.avsc et virement-emis.avsc

Champs selon PRD.MD section 4.1.
Mêmes conventions (namespace, types logiques).

Modifie register-schemas.sh pour tous les schémas.
```

---

#### 2.1.3 : Génération code Go

```text
PROMPT CLAUDE CODE

Crée pkg/events/bancaire.go avec structs Go générées depuis Avro.

Utilise github.com/hamba/avro/v2.
Tags : avro et json.
Types : time.Time, decimal.Decimal.

Tests TDD :
- Sérialisation/désérialisation round-trip
- Tous les types d'événements
```

---

## CHECKPOINT PHASE 2

```bash
./scripts/register-schemas.sh
go test ./pkg/events/...
```

**Checklist :**
- [ ] Schémas .avsc créés
- [ ] Schémas enregistrés dans Schema Registry
- [ ] Types Go générés
- [ ] Tests sérialisation passent

---

# PHASE 3 : Service Simulator

## Objectif

Créer le service qui génère des événements fictifs.

---

### Étape 3.1 : Structure Simulator

#### 3.1.1 : Scaffolding

```text
PROMPT CLAUDE CODE

Crée services/simulator/ :
- cmd/simulator/main.go (bootstrap complet)
- internal/generator/ (génération données)
- internal/api/ (handlers REST)
- Dockerfile (multi-stage)
- go.mod

Main : config, logger, tracer, producer, HTTP server, graceful shutdown.
```

---

#### 3.1.2 : Générateur données fictives

```text
PROMPT CLAUDE CODE

Crée internal/generator/fake_data.go :
- GenerateClientID, GenerateCompteID
- GenerateNom, GeneratePrenom (noms français)
- GenerateMontant(min, max)
- GenerateIBAN (format FR valide)
- GenerateReference

Tests TDD : format valide, déterminisme avec seed.
```

---

#### 3.1.3 : Générateur CompteOuvert

```text
PROMPT CLAUDE CODE

Crée internal/generator/compte_ouvert.go :
- Generate(ctx) : génère et produit un événement
- GenerateBatch(ctx, count, interval)

Tests TDD avec Kafka réel :
- Événement valide produit
- Batch respecte interval
- Annulable via context
```

---

### Étape 3.2 : API Simulator

#### 3.2.1 : Endpoints REST

```text
PROMPT CLAUDE CODE

Crée internal/api/handler.go :

POST /api/v1/simulation/start
  Body: { scenario, rate, duration }
  Response: { simulation_id, status }

POST /api/v1/simulation/stop
  Response: { status, events_produced }

GET /api/v1/simulation/status
  Response: { status, events_produced, rate_actual, started_at }

POST /api/v1/events/produce
  Body: { event_type, count }
  Response: { events_produced, event_ids }

Tests TDD pour chaque endpoint.
```

---

#### 3.2.2 : Gestionnaire simulation

```text
PROMPT CLAUDE CODE

Crée internal/simulation/manager.go :
- SimulationManager avec status atomic
- Start(ctx, config) : goroutine de génération
- Stop() : arrêt propre
- Status() : état courant

Tests TDD : start/stop, auto-stop duration, rate control.
```

---

#### 3.2.3 : Test d'intégration

```text
PROMPT CLAUDE CODE

Crée integration_test.go (build tag: integration)

Tests E2E :
- Démarrer simulation, vérifier événements dans Kafka
- Stop manuel, vérifier arrêt
- Produire événement unique
```

---

## CHECKPOINT PHASE 3

```bash
go test ./services/simulator/...
go test ./services/simulator/... -tags=integration
curl http://localhost:8080/api/v1/simulation/status
```

**Checklist :**
- [ ] Service compile et démarre
- [ ] API /simulation/* fonctionne
- [ ] Événements dans Kafka
- [ ] Dockerfile build réussit

---

# PHASE 4 : Service Bancaire

## Objectif

Créer le service qui consomme et persiste les événements.

---

### Étape 4.1 : Structure Bancaire

#### 4.1.1 : Scaffolding et modèle

```text
PROMPT CLAUDE CODE

Crée services/bancaire/ :
- cmd/bancaire/main.go
- internal/domain/compte.go (Compte, Transaction)
- internal/repository/
- internal/handler/
- migrations/001_create_comptes.sql
- Dockerfile, go.mod

Tables : bancaire.comptes, bancaire.transactions
Index sur client_id et compte_id.
```

---

#### 4.1.2 : Repository Pattern

```text
PROMPT CLAUDE CODE

Crée internal/repository/compte_repository.go :

Interface CompteRepository :
- Create, GetByID, GetByClientID
- UpdateSolde, AddTransaction, GetTransactions

Implémentation PostgresCompteRepository.
Tests TDD avec vraie DB.
```

---

#### 4.1.3 : Handler événements Kafka

```text
PROMPT CLAUDE CODE

Crée internal/handler/event_handler.go :
- HandleCompteOuvert : créer compte (idempotent)
- HandleDepotEffectue : update solde + transaction
- HandleVirementEmis : vérifier solde, débiter
- Route(ctx, msg) : router par topic

Tests TDD : succès, idempotence, erreurs.
```

---

### Étape 4.2 : Intégration Bancaire

#### 4.2.1 : Main et bootstrap

```text
PROMPT CLAUDE CODE

Complète cmd/bancaire/main.go :
- Config, logger, tracer, metrics
- DB pool, repository
- Kafka consumer, subscribe topics
- HTTP server (health + queries)
- Graceful shutdown

Ajoute au docker-compose.yml.
```

---

#### 4.2.2 : API REST queries

```text
PROMPT CLAUDE CODE

Crée internal/api/handler.go :

GET /api/v1/health
GET /api/v1/comptes/:id
GET /api/v1/comptes/:id/transactions
GET /api/v1/clients/:client_id/comptes

Tests TDD pour chaque endpoint.
```

---

#### 4.2.3 : Test E2E Simulator → Bancaire

```text
PROMPT CLAUDE CODE

Crée tests/integration/simulator_bancaire_test.go

Tests E2E :
- Produire CompteOuvert via Simulator, vérifier dans Bancaire
- Flux dépôt : compte + dépôt, vérifier solde
- Multiple events : simulation 10s, vérifier cohérence
- Idempotence : même event 2x, un seul compte

Target Makefile : make test-e2e
```

---

## CHECKPOINT PHASE 4

```bash
go test ./services/bancaire/...
go test ./services/bancaire/... -tags=integration
go test ./tests/integration/... -tags=integration
```

**Checklist :**
- [ ] Service compile et démarre
- [ ] Consumer Kafka fonctionne
- [ ] Données persistées en PostgreSQL
- [ ] API REST /comptes/* fonctionne
- [ ] Test E2E Simulator→Bancaire passe

---

# PHASE 5 : Service Gateway

## Objectif

Créer l'API Gateway avec WebSocket temps réel.

---

### Étape 5.1 : Gateway REST et WebSocket

#### 5.1.1 : Structure et proxy

```text
PROMPT CLAUDE CODE

Crée services/gateway/ :
- cmd/gateway/main.go
- internal/proxy/service_proxy.go
- internal/websocket/hub.go
- internal/api/router.go
- Dockerfile, go.mod

Proxy routes :
- /api/v1/simulation/* → Simulator
- /api/v1/bancaire/* → Bancaire
- /ws → WebSocket

Middleware CORS configuré.
```

---

#### 5.1.2 : WebSocket Hub

```text
PROMPT CLAUDE CODE

Crée internal/websocket/hub.go :
- Hub : clients, broadcast, register/unregister
- Client : conn, send channel, topics map
- Messages : subscribe/unsubscribe par topic

Tests TDD : register, broadcast, topic filtering.
```

---

#### 5.1.3 : Kafka → WebSocket streamer

```text
PROMPT CLAUDE CODE

Crée internal/streaming/kafka_streamer.go :
- Consomme tous les topics bancaire.*
- Broadcast aux clients WebSocket abonnés

Tests d'intégration :
- Client WS reçoit événements Kafka
- Multiple clients reçoivent broadcast
```

---

## CHECKPOINT PHASE 5

```bash
go test ./services/gateway/...
go test ./services/gateway/... -tags=integration
```

**Checklist :**
- [ ] Proxy REST fonctionne
- [ ] WebSocket accepte connexions
- [ ] Subscribe/unsubscribe fonctionnent
- [ ] Événements Kafka streamés via WebSocket

---

# PHASE 6 : Observabilité

## Objectif

Configurer Prometheus et Grafana.

---

### Étape 6.1 : Prometheus

#### 6.1.1 : Configuration

```text
PROMPT CLAUDE CODE

Crée infra/prometheus/prometheus.yml :
- Scrape services : simulator, bancaire, gateway (port 9090)
- Scrape Kafka JMX exporter

Ajoute Prometheus à docker-compose.yml :
- Image : prom/prometheus:v2.47.0
- Port : 9090

Crée scripts/test-prometheus.sh.
```

---

### Étape 6.2 : Grafana Dashboards

#### 6.2.1 : Configuration Grafana

```text
PROMPT CLAUDE CODE

Ajoute Grafana à docker-compose.yml :
- Image : grafana/grafana:10.2.0
- Port : 3000
- Provisioning datasource Prometheus

Crée infra/grafana/provisioning/datasources/prometheus.yml
```

---

#### 6.2.2 : Dashboard Kafka

```text
PROMPT CLAUDE CODE

Crée infra/grafana/dashboards/kafka-overview.json :
- Messages/sec par topic
- Consumer lag par group
- Bytes in/out

Variables : $topic, $consumer_group
```

---

#### 6.2.3 : Dashboard Services

```text
PROMPT CLAUDE CODE

Crée infra/grafana/dashboards/services-overview.json :
- Status services (UP/DOWN)
- Messages produced/consumed
- Latences (heatmap)
- Erreurs
- Ressources (memory, goroutines)
```

---

## CHECKPOINT PHASE 6

```bash
curl http://localhost:9090/api/v1/targets
curl http://localhost:3000/api/health
```

**Checklist :**
- [ ] Prometheus scrape les services
- [ ] Grafana connecté à Prometheus
- [ ] Dashboards affichent les métriques

---

# PHASE 7 : Web UI

## Objectif

Créer l'interface React avec React Flow.

---

### Étape 7.1 : Setup React

#### 7.1.1 : Initialisation

```text
PROMPT CLAUDE CODE

Dans web-ui/, initialise avec Vite + React + TypeScript.

Dépendances :
- @xyflow/react (visualisation)
- @tanstack/react-query (data fetching)
- zustand (state)
- tailwindcss
- axios

Configure Tailwind. Crée structure de base App.tsx.
Crée Dockerfile (multi-stage avec nginx).
```

---

#### 7.1.2 : API et WebSocket clients

```text
PROMPT CLAUDE CODE

Crée src/lib/api.ts :
- simulationApi : start, stop, status, produceEvent
- bancaireApi : getCompte, getTransactions

Crée src/lib/websocket.ts :
- EventSocket : connect, subscribe, unsubscribe

Tests avec MSW.
```

---

### Étape 7.2 : Composants UI

#### 7.2.1 : Contrôles simulation

```text
PROMPT CLAUDE CODE

Crée src/components/SimulationControls.tsx :
- Bouton Start/Stop
- Slider rate
- Input durée
- Status et compteur

Tests avec Testing Library.
```

---

#### 7.2.2 : Visualisation React Flow

```text
PROMPT CLAUDE CODE

Crée src/components/FlowVisualization.tsx :
- Nodes : Simulator, Kafka, Bancaire
- Edges animés selon événements
- Custom FlowNode avec status indicator

Hook useFlowData pour WebSocket → animations.
```

---

#### 7.2.3 : Dashboard métriques

```text
PROMPT CLAUDE CODE

Crée src/components/MetricsDashboard.tsx :
- Cards : events produits, rate, durée
- Status services
- Mini sparklines

Hook useMetrics pour polling/WebSocket.
```

---

### Étape 7.3 : Intégration UI

#### 7.3.1 : Layout final

```text
PROMPT CLAUDE CODE

Assemble dans App.tsx :
- Header avec status connexion
- Sidebar avec contrôles
- Main : FlowVisualization + MetricsDashboard
- Footer avec compteurs

Store Zustand pour état global.
```

---

#### 7.3.2 : Tests E2E Playwright

```text
PROMPT CLAUDE CODE

Installe Playwright.

Crée e2e/simulation.spec.ts :
- Démarre/arrête simulation
- Produit événement manuel
- Vérifie animations
- Vérifie reconnexion WebSocket
```

---

## CHECKPOINT PHASE 7

```bash
cd web-ui && npm test && npm run build
npx playwright test
```

**Checklist :**
- [ ] App React démarre
- [ ] Contrôles Start/Stop fonctionnent
- [ ] Flow animé avec événements
- [ ] WebSocket connecté
- [ ] Tests passent

---

# PHASE 8 : Intégration finale

## Objectif

Valider le système complet.

---

### Étape 8.1 : Tests E2E complets

#### 8.1.1 : Scénarios MVP

```text
PROMPT CLAUDE CODE

Crée tests/e2e/mvp_test.go (build tag: e2e)

Tests :
1. TestMVP_FullFlow : simulation 60s, vérifier tous comptes créés
2. TestMVP_ChaosConsumerRestart : arrêt Bancaire, pas de perte
3. TestMVP_HighThroughput : rate=100, vérifier stabilité
```

---

#### 8.1.2 : Script validation

```text
PROMPT CLAUDE CODE

Crée scripts/validate-mvp.sh :
1. make infra-up
2. make test-infra
3. make services-up
4. make test-unit
5. make test-integration
6. make test-e2e
7. Vérifier Prometheus targets
8. Simulation 30s via API
9. Cleanup

Target : make validate-mvp
```

---

#### 8.1.3 : Tests performance

```text
PROMPT CLAUDE CODE

Crée tests/e2e/performance_test.go (build tag: performance)

Tests :
- Throughput : rate=100, vérifier >= 90%
- Latency : P50, P95, P99 < 500ms
- Burst : 1000 events/1s, traitement < 30s
- Sustained : 5 min stable, pas de memory leak

Script : scripts/run-performance-tests.sh
Dashboard : infra/grafana/dashboards/performance.json
```

---

### Étape 8.2 : Documentation

#### 8.2.1 : README

```text
PROMPT CLAUDE CODE

Crée README.md complet :
- Quick start (3 commandes)
- Architecture (diagramme ASCII)
- Utilisation (simulation, visualisation, métriques)
- Développement (structure, tests)
```

---

#### 8.2.2 : Documentation technique

```text
PROMPT CLAUDE CODE

Crée docs/ARCHITECTURE.md :
- Diagrammes C4
- Flux de données détaillé
- Liens vers ADRs

Crée docs/adr/ :
- 001-choix-kafka.md
- 002-choix-avro.md
- 003-choix-go.md
- 004-choix-postgresql.md
- 005-choix-react-flow.md
```

---

#### 8.2.3 : Guide Pub/Sub

```text
PROMPT CLAUDE CODE

Crée docs/patterns/01-pub-sub.md :
- Concept et diagramme
- Implémentation EDA-Lab (code examples)
- Exercices pratiques
- Compromis architecturaux
- Lien vers patron suivant
```

---

## CHECKPOINT PHASE 8 (FINAL)

```bash
make validate-mvp
```

**Checklist MVP complète :**
- [ ] Infrastructure : Kafka, Schema Registry, PostgreSQL
- [ ] Services : Simulator, Bancaire, Gateway
- [ ] Observabilité : Prometheus, Grafana
- [ ] Web UI : React Flow, contrôles, métriques
- [ ] Tests : unit, integration, e2e, performance
- [ ] Documentation : README, architecture, patterns

---

## Commandes de validation rapide

```bash
# Démarrer tout
make infra-up && make services-up

# Tester tout
make test-unit && make test-integration && make test-e2e

# Validation complète
make validate-mvp

# Cleanup
make infra-down
```

---

## Notes d'implémentation

1. **Ordre strict** : Chaque sous-étape dépend des précédentes
2. **TDD** : Tests avant implémentation
3. **Données réelles** : testcontainers-go et Docker Compose
4. **Intégration continue** : Code fonctionnel à chaque étape
5. **Validation** : Tests après chaque sous-étape

---

**Dernière mise à jour :** 2026-01-20

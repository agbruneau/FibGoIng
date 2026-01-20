# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EDA-Lab** is an academic simulation platform for learning Event Driven Architecture (EDA) patterns. It simulates a French financial services ecosystem (banking, personal insurance, damage insurance) interconnected through event-driven architecture.

## Tech Stack

- **Backend**: Go 1.21+ (monorepo with Go workspace)
- **Message Broker**: Confluent Kafka (KRaft mode, no ZooKeeper)
- **Schema Registry**: Confluent Schema Registry with Apache Avro
- **Database**: PostgreSQL 16
- **Frontend**: React + Vite + React Flow + Tailwind CSS (planned)
- **Containerization**: Docker Compose (Windows 11/WSL2)

## Build & Development Commands

```bash
# Infrastructure
make infra-up              # Start Kafka, Schema Registry, PostgreSQL
make infra-down            # Stop all containers
make infra-logs            # View container logs
make infra-clean           # Remove volumes and restart fresh
make test-infra            # Validate infrastructure health

# Kafka
make kafka-topics          # List all topics
make kafka-create-topic TOPIC=name

# Go
go build ./cmd/...         # Build services
go test ./...              # Run all tests
go test -race ./...        # Tests with race detector

# Testing
make test-unit             # Unit tests
make test-integration      # Integration tests (requires infra-up)
make test-e2e              # End-to-end tests
```

## Architecture

```
Simulator → Kafka → Bancaire → PostgreSQL
    ↓          ↓
Gateway (REST/WS) → web-ui (React Flow)
```

**Kafka Topic Naming**: `<domain>.<entity>.<action>` (e.g., `bancaire.compte.ouvert`)

**Avro Namespace Convention**: `com.edalab.<domain>.events`

## Project Structure (Target)

```
services/           # Go microservices (simulator, bancaire, gateway)
pkg/                # Shared Go packages (config, kafka, database, events, observability)
schemas/            # Avro schema files (.avsc)
infra/              # Docker Compose and infrastructure config
web-ui/             # React frontend
scenarios/          # YAML test scenarios
scripts/            # Bash utility scripts
tests/              # integration/ and e2e/ test suites
```

## Development Approach

This project follows **Test Driven Development (TDD)** with incremental phases:

1. **RED**: Write failing test first
2. **GREEN**: Implement minimal solution to pass
3. **REFACTOR**: Improve without changing behavior

See PLAN.MD for detailed phase prompts (Phases 0-8).

## Key Dependencies

| Purpose | Library |
|---------|---------|
| Kafka client | `github.com/segmentio/kafka-go` |
| Schema Registry | `github.com/riferrei/srclient` |
| PostgreSQL | `github.com/jackc/pgx/v5` |
| Avro | `github.com/hamba/avro/v2` |
| Decimals | `github.com/shopspring/decimal` |
| Config | `gopkg.in/yaml.v3` |

## Environment Variables

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=edalab
POSTGRES_USER=edalab
POSTGRES_PASSWORD=edalab_password
```

## Documentation Map

- **PRD.MD**: Product requirements, domain events catalog, EDA patterns (WHAT to build)
- **PLAN.MD**: Technical implementation phases with Claude Code prompts (HOW to build)

<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# fonder sur github SpecKit. Lister les premiers les livrables md à produire afin camper ce projet.

Créez un repo GitHub `agbruneau/SpecKit` (fork/inspiré [github/spec-kit](https://github.com/github/spec-kit), toolkit spec-driven dev 60k⭐).[web: repos] Voici les 5 premiers livrables Markdown prioritaires pour camper AgentMesh-Kafka (interop agentique EDA) ; générez-les via Cursor/Claude pour bootstrap.

## 1. README.md (Priorité \#1)

```
# SpecKit - AgentMesh Kafka Interop Toolkit
[![Go](https://img.shields.io/badge/Go-1.24-blue)](...) [![Rust](...)] [![License MIT](...)]

## Aperçu
Toolkit spec-driven pour maillage agentique sur Kafka (EDA interop).

## Quickstart
```bash
make init  # Docker Kafka + agents
cargo run -- agent order-producer
```


## Stack

- Kafka + AsyncAPI
- Agents Claude/Gemini

```

## 2. ROADMAP.md
```


# Roadmap SpecKit v1.0

## v0.1 MVP (1 semaine)

- [ ] Producer agents (Go)
- [ ] Consumer mesh (Rust)
- [ ] TUI dashboard


## v0.2 (2 sem)

- [ ] DLQ/retry agentic
- [ ] AsyncAPI gen specs


## v1.0

- Kubernetes Helm
- Benchmarks 10k TPS

```

## 3. adr/001-use-kafka-edr.md (Architecture Decision Record)
```


# ADR 001: Kafka comme Broker EDA

## Statut: Accepté

## Contexte: Interop agents découplés

## Décision: Kafka (KRaft) vs NATS/Rabbit

Pros: Scalable, exactly-once, CloudEvents native.
Cons: Complexité ops (mitigée Docker).

```

## 4. CONTRIBUTING.md
```


# Contribution

## Setup

```bash
make dev-up
cargo test
```

Fork → PR → Review (Claude assist).
Specs-first: Update AsyncAPI avant code.

```

## 5. docs/architecture.md
```


# Architecture AgentMesh

## Overview

```
[Diagram Mermaid: agents → Kafka topics → consumers]
```


## Protos

- CloudEvents v1.0
- AsyncAPI pour discovery

```

Committez ces MD → `git push origin main` ; ajoutez .gitignore/CI (GitHub Actions). Prochain : proto code producer. Aide génération ?[web: repos]```


<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# SpecKit.plan.md - Plan Technique AgentMesh-Kafka

**Version**: 0.1.0
**Auteur**: agbruneau
**Date**: 2026-01-07
**Stack Choisie**: Go (core/performance) + Rust (agents parallèles) + Kafka 3.7 (KRaft) + AsyncAPI/CloudEvents
**Durée Estimée**: 4 semaines MVP (iteratif spec-driven).

## 🎯 Constitution Projet (Alignée speckit.specify.md)

- **Principes** : Specs-first (AsyncAPI générée → code), interop CloudEvents v1.0, zéro-downtime (DLQ/retry).
- **Contraintes** : MIT License, Docker-native, <100ms latence mesh, 10k TPS.


## 🏗️ Architecture Haute-Niveau

```
graph TB
  CLI[SpecKit CLI] --> SPEC[AsyncAPI YAML]
  SPEC --> STUBS[Stubs Go/Rust]
  STUBS --> DOCKER[Docker Compose]
  Agents[Agents Mesh] <--> Kafka[Kafka Topics]
```

- **Couche Specs** : AsyncAPI + Protobuf schemas.
- **Couche Runtime** : Kafka broker + agents (producer/consumer/discovery).
- **Observabilité** : Prometheus + TUI (Bubble Tea).


## 📦 Stack Technique Détaillée

| Composant | Tech | Rationale |
| :-- | :-- | :-- |
| CLI Generator | Go (cobra) | Facile CLI, intégration Buf/AsyncAPI |
| Agents Producer | Go (confluent-kafka-go) | Perf streaming, zéro-alloc |
| Agents Consumer | Rust (rdkafka) | Parallélisme Rayon, safety |
| Schemas | Protobuf + AsyncAPI CLI | Interop machine-readable |
| Infra | Docker Compose + KRaft | No ZK, local/prod |
| Test | GoTest/Rust cargo-test + k6 | 95% coverage, load 10k TPS |
| CI/CD | GitHub Actions | Lint, generate, deploy demo |

## 📅 Phases \& Milestones (Gantt Inspiré)

| Phase | Durée | Livrables | Dépendances | Risques |
| :-- | :-- | :-- | :-- | :-- |
| **0.1 Specs** (Sem1) | 3j | AsyncAPI YAML validé, schemas proto | speckit.specify.md | Schema compat (M) |
| **0.2 CLI** (Sem1) | 4j | `spec-kit generate` stubs | Phase 0.1 | Tooling Buf (L) |
| **0.3 MVP Agents** (Sem2) | 1s | Producer/consumer Docker, mesh E2E | Phase 0.2 | Kafka perf (M) |
| **0.4 Observabilité** (Sem3) | 3j | TUI dashboard, Prometheus | Phase 0.3 | UI Rust (L) |
| **0.5 Polish/Release** (Sem4) | 1s | README, CI, benchmarks, tags v1.0 | All | - |

**Total** : 4 semaines ; **MVP testable Sem2** (git tag v0.3).

## 🔧 Détails Implémentation

### 1. CLI Generator (`cmd/spec-kit`)

```go
// Exemple sortie
spec-kit generate --input speckit.specify.md --output ./generated/
# → asyncapi/agentmesh.yaml
# → proto/order.pb.go
# → docker-compose.yml
```


### 2. Agents Structure

```
agents/
├── producer/  # Go: publish CloudEvents
├── consumer/  # Rust: subscribe, Claude reasoning
└── discovery/ # Poll AsyncAPI changes
```


### 3. Test Plan

- Unit: Schemas validation (Buf).
- Intégration: Docker Kafka full mesh.
- Load: k6 → 10k TPS, 99% success.


### 4. Quickstart Généré

```bash
# Auto-généré depuis spec
make up  # Kafka + agents
curl -X POST /order  # Trigger mesh
```


## ⚠️ Risques \& Mitigations

| Risque | Prob | Impact | Mitigation |
| :-- | :-- | :-- | :-- |
| Kafka ops | M | H | Docker KRaft only |
| Schema drift | H | H | Buf breaking-change check |
| Agent reasoning fail | M | M | Fallback retry + logs |

**Prochain** : Exécutez `/speckit.tasks` pour tasks granulaire ; implémentez Phase 0.1 via Cursor/Claude. ![^1][^2][^3]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: http://www.scitepress.org/DigitalLibrary/Link.aspx?doi=10.5220/0003504300440053

[^2]: https://www.redpanda.com/guides/kafka-use-cases-event-driven-architecture

[^3]: https://github.com/github/spec-kit

[^4]: https://www.semanticscholar.org/paper/d0d6addd07c4caaace12c95d9f3c662678b0a50e

[^5]: https://www.semanticscholar.org/paper/5e94b3e3229995df495e65a65c4b697aafbd802d

[^6]: http://link.springer.com/10.1007/978-3-642-36177-7_8

[^7]: http://aircconline.com/vlsics/V9N3/9318vlsi04.pdf

[^8]: https://www.semanticscholar.org/paper/3e07b381b0a373560fc0431d276fca3629edce8f

[^9]: https://www.semanticscholar.org/paper/167e30fbdfabeb41e7250b9ca7f33d66a81db85b

[^10]: https://www.taylorfrancis.com/books/9781439897553

[^11]: http://ij-healthgeographics.biomedcentral.com/articles/10.1186/1476-072X-4-2

[^12]: https://www.semanticscholar.org/paper/262ab31f7a7f7a63c96caec494f458c3eeee2463

[^13]: https://arxiv.org/pdf/2410.10762.pdf

[^14]: https://arxiv.org/html/2412.17029v1

[^15]: https://arxiv.org/pdf/2501.17167.pdf

[^16]: https://arxiv.org/pdf/2408.08435.pdf

[^17]: https://arxiv.org/html/2501.07834

[^18]: https://arxiv.org/pdf/2412.04093.pdf

[^19]: https://arxiv.org/html/2410.08164

[^20]: https://arxiv.org/pdf/2404.17017.pdf

[^21]: https://www.confluent.io/learn/event-driven-architecture/

[^22]: https://www.gravitee.io/blog/event-driven-architecture-patterns

[^23]: https://www.kai-waehner.de/blog/2025/04/14/how-apache-kafka-and-flink-power-event-driven-agentic-ai-in-real-time/

[^24]: https://www.linkedin.com/pulse/event-driven-architecture-kafka-step-by-step-poc-guide-rajesh-paleru-pf0we

[^25]: https://arxiv.org/html/2505.02279v1

[^26]: https://developers.redhat.com/articles/2025/06/16/how-kafka-improves-agentic-ai

[^27]: https://developer.microsoft.com/blog/spec-driven-development-spec-kit

[^28]: https://doc.milestonesys.com/latest/en-US/wp_xpr_aws/target_customers_and_deployment.htm

[^29]: https://dzone.com/articles/agentic-ai-using-apache-kafka-as-event-broker-with-agent2agent-protocol

[^30]: https://github.com/github/spec-kit/blob/main/spec-driven.md

[^31]: https://www.sei.cmu.edu/documents/2122/2006_004_001_14735.pdf

[^32]: https://covalensedigital.com/resources/blogs/event-driven-architecture

[^33]: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/

[^34]: https://www.ibm.com/docs/SSHEB3_3.8/pdfs_wiki/Gantt_Milestones_and_Planned_Tasks.pdf

[^35]: https://cndi.dev/templates/kafka

[^36]: https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html

[^37]: https://ehealthontario.on.ca/files/public/support/Architecture/EHR_Interoperability_Plan.pdf

[^38]: https://www.epam.com/insights/ai/blogs/inside-spec-driven-development-what-githubspec-kit-makes-possible-for-ai-engineering


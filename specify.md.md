<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# SpecKit.specify.md - Template Spécification AgentMesh-Kafka

**Version**: 0.1.0
**Auteur**: agbruneau
**Date**: 2026-01-07
**Statut**: Draft (Spec-Driven Development)
**Outils**: AsyncAPI 3.0 + CloudEvents 1.0 + Protobuf Schemas

## 🎯 Aperçu Projet

SpecKit génère specs machine-readable pour maillage agentique sur Kafka : agents producer/consumer découplés via EDA interop (AsyncAPI/CloudEvents).
**Objectif** : Toolkit CLI générant code stubs (Go/Rust) depuis specs.
**Cas d'usage** : E-commerce orders → inventory → billing agents.

## 📋 Exigences Fonctionnelles

| ID | Description | Priorité |
| :-- | :-- | :-- |
| RF-001 | Générer AsyncAPI YAML depuis template Markdown | Haut |
| RF-002 | Valider CloudEvents schemas (JSON/Protobuf) | Haut |
| RF-003 | Générer stubs Go/Rust (producer/consumer) | Moyen |
| RF-004 | TUI preview Kafka topics/mesh | Bas |

## 🔌 Spécification AsyncAPI (Exemple Généré)

```yaml
asyncapi: '3.0.0'
info:
  title: AgentMesh-Kafka Interop
  version: 1.0.0
  description: Maillage agentique EDA
servers:
  prod:
    host: 'kafka://broker:9092'
    protocol: kafka
    protocolVersion: '3.7'
channels:
  orders/v1/{orderId}:
    address:
      $param:
        orderId: { description: Unique order UUID }
    messages:
      orderPlaced:
        name: OrderPlaced
        contentType: application/cloudevents+json
        payload:
          $ref: '#/components/schemas/OrderEvent'
  inventory/{orderId}/reply:
    messages:
      inventoryChecked:
        payload:
          $ref: '#/components/schemas/InventoryEvent'
```


## ☁️ CloudEvents Schemas (Interop Standard)

### OrderPlaced (Producer → Kafka)

```json
{
  "specversion": "1.0",
  "id": "uuid-123",
  "source": "order-agent",
  "type": "com.agentmesh.order.placed",
  "datacontenttype": "application/json",
  "data": {
    "orderId": "ORD-001",
    "customerId": "CUST-123",
    "items": [{"sku": "COFFEE", "qty": 2}]
  },
  "dataschema": "https://raw.githubusercontent.com/agbruneau/SpecKit/main/schemas/order.proto"
}
```


### InventoryChecked (Reply Topic)

```protobuf
syntax = "proto3";
message InventoryEvent {
  string orderId = 1;
  bool available = 2;
  repeated string unavailableSkus = 3;
}
```


## 🏗️ Architecture Mesh

```
Mermaid Diagram:
graph TD
  A[OrderAgent] -->|orderPlaced| K[Kafka orders/v1]
  K --> B[InventoryAgent]
  B -->|inventoryChecked| R[Kafka reply/v1]
  R --> C[BillingAgent]
  D[DiscoveryAgent] -.->|AsyncAPI| K
```


## 🔍 Contraintes Non-Fonctionnelles

| Critère | Valeur |
| :-- | :-- |
| Throughput | 10k TPS (Kafka) |
| Latence | <100ms E2E mesh |
| Résilience | DLQ + retry (exponential backoff) |
| Interop | CloudEvents v1.0 + AsyncAPI 3.0 |
| Sécurité | SASL/SCRAM + mTLS |

## 📊 Métriques Succès

- 95% events processed sans retry.
- Specs valident 100% stubs générés.
- Mesh auto-discover 10+ agents.


## 🚀 Génération Code (CLI Output)

```
spec-kit generate --spec speckit.specify.md --lang go
→ cmd/agent/producer.go
→ internal/proto/order.pb.go
→ docker-compose.kafka.yml
```

**Prochain** : Implémentez CLI generator (Buf/AsyncAPI CLI). Utilisez Cursor pour stubs depuis cette spec ![^1][^2][^3]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.asyncapi.com/docs/tutorials/kafka

[^2]: https://www.asyncapi.com/docs/reference/specification/v3.0.0

[^3]: https://www.tmforum.org/resources/guidebook/ig1412-ai-agent-specification-template-v1-0-0/

[^4]: https://www.semanticscholar.org/paper/6e619e92ee200374d4b00f6fe9842788bdae24c5

[^5]: https://www.semanticscholar.org/paper/ca93ec8d30865319d667874826ca94cea7f6ca96

[^6]: https://www.semanticscholar.org/paper/068509df014d2fcb49f63935c711f885591d0845

[^7]: https://arxiv.org/pdf/2410.10762.pdf

[^8]: https://arxiv.org/pdf/2308.04189.pdf

[^9]: https://arxiv.org/pdf/2502.17443.pdf

[^10]: https://arxiv.org/pdf/2402.05102.pdf

[^11]: https://arxiv.org/pdf/2410.21620.pdf

[^12]: https://linkinghub.elsevier.com/retrieve/pii/S138376212100151X

[^13]: http://arxiv.org/pdf/2410.15533.pdf

[^14]: https://arxiv.org/pdf/2502.13965.pdf

[^15]: https://solace.com/blog/streamlining-eda-design-asyncapi-code-gen-event-portal/

[^16]: https://specmatic.io/appearance/kafka-and-jms-mocking-with-asyncapi-using-specmatic/

[^17]: https://www.asyncapi.com/blog/understanding-asyncapis

[^18]: https://learn.microsoft.com/en-us/azure/event-grid/cloud-event-schema

[^19]: https://www.linkedin.com/pulse/solution-approach-real-time-edge-multi-agentic-ai-tml-maurice-ph-d--abmoc

[^20]: https://www.confluent.io/events/kafka-summit-americas-2021/how-to-define-and-share-your-event-apis-using-asyncapi-and-event-api/

[^21]: https://www.youtube.com/watch?v=FhDybT7cFAk

[^22]: https://www.redpanda.com/guides/kafka-use-cases-event-driven-architecture

[^23]: https://cdevents.dev/docs/primer/

[^24]: https://tenzindayoe.com/work/agentmesh

[^25]: https://dev.to/raphaeldelio/asyncapi-a-standard-specification-for-documenting-event-driven-applications-4dep

[^26]: https://aws.amazon.com/blogs/compute/sending-and-receiving-cloudevents-with-amazon-eventbridge/

[^27]: https://www.gravitee.io/blog/best-practices-principles-for-agent-mesh-implementations

[^28]: https://www.youtube.com/watch?v=GQXRW5C6U0s

[^29]: https://cloudevents.io

[^30]: https://developers.redhat.com/articles/2025/06/16/how-kafka-improves-agentic-ai

[^31]: https://github.com/asyncapi/spec/blob/master/examples/adeo-kafka-request-reply-asyncapi.yml


Voici le fichier `PLAN.md`. Il sert de feuille de route d'ingénierie, découpant la complexité architecturale en modules gérables et en phases séquentielles.

Ce plan privilégie une approche **"Infrastructure-First"** : on ne code pas d'agents tant que le système nerveux (Kafka + Schémas) n'est pas opérationnel.

---

# PLAN.md - Plan d'Implémentation & Architecture Technique

> **Projet :** Agent Mesh Kafka (Transformation `habit-tracker`)
> **Stratégie :** Incremental Strangler Fig Pattern

## 1. Architecture de Référence

Le système est conçu comme un pipeline de données réactif en boucle fermée.

```mermaid
graph TD
    subgraph "Legacy Zone"
        UI[React Frontend] --> API[FastAPI Backend]
        API --> DB[(SQLite/Postgres)]
        API -.->|Async Producer| K_RAW
    end

    subgraph "Cognitive Mesh (Kafka)"
        K_RAW(Topic: habit.telemetry.raw)
        K_PAT(Topic: habit.analysis.patterns)
        K_CMD(Topic: agent.output.commands)
    end

    subgraph "Agentic Layer (Python)"
        Obs[Observer Agent] -- Consumer --> K_RAW
        Obs -- Producer --> K_PAT
        
        Coach[Coach Agent (LLM)] -- Consumer --> K_PAT
        Coach -- Producer --> K_CMD
    end

    subgraph "Actuator Layer"
        Notifier[Notification Service] -- Consumer --> K_CMD
        Notifier --> User(Mobile/Email)
    end

```

---

## 2. Modules & Responsabilités

| Module | Stack Technique | Responsabilité | Type |
| --- | --- | --- | --- |
| **`infra-core`** | Docker, Kafka, Schema Registry | L'infrastructure runtime. Contient les `docker-compose.yml` et scripts d'init. | Infra |
| **`schema-registry`** | Avro (`.avsc`) | La Source de Vérité. Contient les contrats d'interface. | Data |
| **`habit-tracker-api`** | Python (FastAPI), `confluent-kafka` | Le système Legacy instrumenté. Agit comme "Capteur". | Source |
| **`agent-observer`** | Python, Faust ou Vanilla Consumer | Analyse déterministe (Statistiques, Streaks). | Processor |
| **`agent-coach`** | Python, LangChain/LangGraph | Analyse probabiliste (LLM) et prise de décision. | Processor |
| **`service-notifier`** | Python, SMTP/Firebase | Exécuteur des commandes ("Side effects"). | Sink |

---

## 3. Contrats d'Interface (Schema Definition)

L'interopérabilité repose sur ces définitions Avro strictes.

### A. Télémétrie (`habit.telemetry.raw`)

*Event : L'utilisateur a fait (ou défait) quelque chose.*

```json
// events/habit_log_recorded.avsc
{
  "type": "record",
  "name": "HabitLogRecorded",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "timestamp_utc", "type": "long"},
    {"name": "user_id", "type": "string"},
    {"name": "habit_id", "type": "string"},
    {"name": "action_type", "type": {"type": "enum", "symbols": ["LOG", "UNLOG"]}},
    {"name": "metadata", "type": ["null", "map"], "values": "string"}
  ]
}

```

### B. Insights (`habit.analysis.patterns`)

*Event : L'Agent Observateur a remarqué quelque chose.*

```json
// events/pattern_detected.avsc
{
  "type": "record",
  "name": "PatternDetected",
  "fields": [
    {"name": "analysis_id", "type": "string"},
    {"name": "target_user_id", "type": "string"},
    {"name": "pattern_type", "type": {"type": "enum", "symbols": ["STREAK_BROKEN", "INCONSISTENT_TIME", "MILESTONE_REACHED"]}},
    {"name": "confidence_score", "type": "float"},
    {"name": "supporting_data", "type": "string"} // JSON dump des preuves
  ]
}

```

### C. Commandes (`agent.output.commands`)

*Command : L'Agent Coach demande une action.*

```json
// commands/send_notification.avsc
{
  "type": "record",
  "name": "SendNotificationCommand",
  "fields": [
    {"name": "command_id", "type": "string"},
    {"name": "recipient_id", "type": "string"},
    {"name": "channel", "type": {"type": "enum", "symbols": ["PUSH", "EMAIL", "IN_APP"]}},
    {"name": "content_body", "type": "string"},
    {"name": "tone", "type": "string", "default": "neutral"}
  ]
}

```

---

## 4. Ordre d'Implémentation (Phasing)

### Phase 1 : Les Fondations (Jours 1-2)

*Objectif : Pipeline de données fonctionnel (Hello World).*

1. **Setup Docker :** Monter Kafka, Zookeeper, Schema Registry et Kafka UI.
2. **Schema Registration :** Script Python pour pousser les fichiers `.avsc` vers le Schema Registry au démarrage.
3. **Test Plumbing :** Vérifier qu'on peut publier un message Avro manuellement et le lire via Kafka UI.

### Phase 2 : Instrumentation du Legacy (Jours 3-4)

*Objectif : Le `habit-tracker` parle.*

1. **Refactor FastAPI :** Créer un singleton `KafkaProducerWrapper`.
2. **Intercept Writes :** Dans `main.py` (ou service layer), après `db.add(log)`, appeler `producer.send()`.
3. **Validation :** Utiliser l'app React, créer une habitude, vérifier l'apparition du message dans le topic `habit.telemetry.raw`.

### Phase 3 : L'Agent Observateur (Jours 5-6)

*Objectif : Traitement déterministe.*

1. **Skeleton :** Créer un service Python simple qui boucle sur `consumer.poll()`.
2. **Logic :** Implémenter une détection simple (ex: si `timestamp` est entre 2h et 5h du matin -> flag "Insomnie").
3. **Produce :** Publier le résultat dans `habit.analysis.patterns`.

### Phase 4 : L'Agent Coach & LLM (Jours 7-9)

*Objectif : Intelligence Artificielle.*

1. **Integration LLM :** Setup de l'API Key (Claude/Gemini).
2. **Prompt Engineering :** Créer le System Prompt : *"Tu es un coach comportemental. Analyse ce pattern JSON..."*
3. **Cycle complet :** Consumer (Pattern) -> LLM -> Producer (Command).

### Phase 5 : Fermeture de la boucle (Jour 10+)

*Objectif : Impact utilisateur.*

1. **Notifier Service :** Un consommateur simple qui print les commandes dans la console (Mock) ou envoie un vrai email.
2. **AgentOps :** Ajouter des logs structurés pour tracer le `trace_id` à travers les 4 étapes.

---

## 5. Standards de Développement

* **Gestion des Erreurs :**
* Si un agent échoue à traiter un message (ex: format invalide), envoyer vers un topic `dead-letter-queue` (DLQ). Ne jamais crasher la boucle de consommation.


* **Idempotence :**
* Les consommateurs doivent assumer qu'un message peut arriver deux fois (`at-least-once delivery`). Utiliser `event_id` pour dédoublonner si critique.


* **Sécurité :**
* Pas de clés API dans le code. Utiliser `.env`.
* Le `Producer` doit utiliser une authentification SASL/Plain (même en local, pour simuler la prod).
Voici le fichier `MAIN.md`. Il traduit la vision stratégique en spécifications techniques exécutables.

Ce document adopte une approche **Behavior-Driven Design (BDD)** adaptée aux systèmes distribués, mettant l'accent sur les contrats d'interface (Schemas) et les flux de données.

---

# MAIN.md - Spécifications Fonctionnelles & Techniques

> **Projet :** Transformation Agentique `habit-tracker`
> **Architecture :** Event-Driven Agent Mesh (Kafka)
> **Pattern :** Cognitive Sidecar

## 1. Vue d'Ensemble du Système

Le système transforme l'application monolithique `habit-tracker` en un producteur de télémétrie. L'intelligence métier est déportée vers un maillage d'agents autonomes qui observent, analysent et agissent via un bus d'événements Kafka.

### Le Cycle Cognitif (The Cognitive Loop)

1. **Senser (Percevoir) :** L'app capture une action utilisateur.
2. **Think (Raisonner) :** Les agents détectent des patterns et décident d'une stratégie.
3. **Act (Agir) :** Le système notifie l'utilisateur ou met à jour l'état.

---

## 2. User Stories & Épics

### Épic A : Télémétrie & Perception (Le "Senser")

> **Objectif :** Découpler la capture de donnée de son traitement.

* **US-A1 : Instrumentation des Logs**
* *En tant que* Système Source (FastAPI),
* *Je veux* publier un événement `HabitLogCreated` sur Kafka à chaque insertion en base,
* *Afin que* les agents puissent réagir en temps quasi-réel sans poller la base de données.


* **US-A2 : Ingestion de Contexte**
* *En tant qu'* Agent Observateur,
* *Je veux* recevoir les métadonnées de l'habitude (fréquence cible, description),
* *Afin de* comprendre si une absence de log est normale ou critique.



### Épic B : Intelligence & Coaching (Le "Think")

> **Objectif :** Remplacer la logique conditionnelle rigide par un raisonnement probabiliste.

* **US-B1 : Détection de Décrochage (Observer Agent)**
* *En tant qu'* Agent Observateur,
* *Je veux* identifier une rupture de séquence (Streak break) ou un changement d'heure de log,
* *Afin de* publier un événement `PatternDetected` (ex: "Risque d'abandon élevé").


* **US-B2 : Coaching Personnalisé (Coach Agent)**
* *En tant qu'* Agent Coach,
* *Je veux* consommer les `PatternDetected` et générer un message de motivation contextuel via LLM (Claude/Gemini),
* *Afin de* maximiser l'engagement utilisateur sans être intrusif.



### Épic C : Gouvernance & Action (Le "Act" & "Audit")

> **Objectif :** Garantir la sécurité et l'explicabilité.

* **US-C1 : Barrière de Sécurité (Guardrails)**
* *En tant que* Système,
* *Je veux* bloquer tout message sortant contenant des hallucinations ou un ton inapproprié,
* *Afin de* protéger l'utilisateur final.


* **US-C2 : Traçabilité des Décisions**
* *En tant qu'* Auditeur,
* *Je veux* voir le lien de causalité entre `HabitLogCreated` -> `PatternDetected` -> `CoachAction`,
* *Afin de* debugger pourquoi l'IA a suggéré une action spécifique.



---

## 3. Flows & Chorégraphie (Workflows)

### Flux Principal : "De l'Action à la Réaction"

1. **Ingestion (Source)**
* **Trigger :** Utilisateur logue une activité (`POST /log`).
* **Action :** FastAPI commit en DB locale + Produce message.
* **Topic :** `habit.telemetry.raw`
* **Payload (Avro) :** `{"user_id": "u1", "habit_id": "h1", "timestamp": 17000000, "value": 1}`


2. **Analyse (Observer Agent - Python)**
* **Input :** Consomme `habit.telemetry.raw`.
* **State Store :** Récupère l'historique récent (Windowed aggregation via Kafka Streams/Flink ou mémoire locale).
* **Processing :** Calcule les métriques dérivées.
* **Output Topic :** `habit.analysis.insights`
* **Payload (Avro) :** `{"type": "STREAK_AT_RISK", "confidence": 0.85, "context": "No log for 48h"}`


3. **Décision (Coach Agent - LLM)**
* **Input :** Consomme `habit.analysis.insights`.
* **Processing :** Construit le prompt -> Appel LLM (Claude 3.5 Sonnet).
* **Interne :** Publie la "Pensée" sur `agent.internal.thoughts` (ex: "User needs gentle nudge, not alert").
* **Output Topic :** `agent.commands.outbox`
* **Payload (Avro) :** `{"action": "SEND_NOTIFICATION", "content": "Hey, missed yesterday? Easy win today!", "channel": "MOBILE_PUSH"}`


4. **Exécution (Sink)**
* **Input :** Consomme `agent.commands.outbox`.
* **Action :** Appel API Notification (Firebase/Email).



---

## 4. Contraintes Techniques (Non-Functional Requirements)

### Architecture

1. **Strict Schema Registry :** Aucun message ne transite sans validation Avro. Les évolutions de schéma doivent être rétro-compatibles (`BACKWARD`).
2. **Idempotence :** Les agents doivent gérer la réception en doublon d'un même message (ex: via `interaction_id` unique).
3. **Stateless Compute :** Les agents ne stockent pas d'état persistant local critique. En cas de crash, ils reconstruisent leur état en relisant le Topic (Replay).

### Performance & Latence

1. **Latence de bout en bout :** < 10 secondes (du log utilisateur à la notification IA).
2. **Backpressure :** Le système doit supporter un pic de charge sans crasher (les messages s'accumulent dans Kafka, pas en RAM).

### Sécurité (AgentSec)

1. **Sanitization :** Les données PII (si ajoutées) doivent être masquées ou tokenisées avant l'envoi au LLM externe.
2. **Output Validation :** Tout JSON généré par le LLM doit être validé syntaxiquement avant publication.

---

## 5. Critères d'Acceptation (Definition of Done)

### Niveau 1 : Infrastructure (MVP)

* [ ] Le cluster Kafka est opérationnel avec Schema Registry.
* [ ] L'application FastAPI publie des événements valides lors des opérations CRUD.
* [ ] Les schémas Avro `HabitLog` et `AgentCommand` sont versionnés.

### Niveau 2 : Intelligence

* [ ] L'Agent Observateur détecte correctement un "trou" de 2 jours dans les logs.
* [ ] L'Agent Coach génère 3 variations de messages différents pour le même événement (preuve de non-déterminisme contrôlé).
* [ ] La trace complète de la décision est visible dans le topic `agent.internal.thoughts`.

### Niveau 3 : Robustesse

* [ ] Si l'Agent Coach est éteint pendant 1 heure puis rallumé, il traite tout le backlog sans erreur.
* [ ] Une injection de message malformé dans `habit.telemetry.raw` est rejetée par le consommateur (Dead Letter Queue) et ne plante pas l'agent.
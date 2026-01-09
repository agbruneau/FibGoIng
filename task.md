Voici le fichier `TASK.md`. Il est conçu comme un **Backlog Technique** prêt à l'emploi.

J'ai décomposé le plan en unités de travail atomiques (ticketable items), en précisant pour chaque tâche la "Definition of Done" (DoD) technique. C'est le document de référence pour le développeur (vous) au jour le jour.

---

# TASK.md - Backlog & Suivi d'Implémentation

> **État du Projet :** 🏗 Phase 1 (Infrastructure)
> **Sprint Actuel :** 01 - Genesis

Ce fichier liste les tâches techniques nécessaires pour transformer `coleam00/habit-tracker` en un système **Agent Mesh**. Cochez les cases (`[x]`) au fur et à mesure de votre progression.

---

## 🛑 Phase 0 : Prérequis & Environnement

*Avant de coder, l'établi doit être prêt.*

* [ ] **Setup Repository**
* [ ] Cloner `coleam00/habit-tracker`.
* [ ] Créer la branche `feat/agent-mesh-init`.
* [ ] Restructurer les dossiers selon `README.md` (créer `/infrastructure`, `/schemas`, `/agents`).


* [ ] **Accès API**
* [ ] Obtenir clé API Anthropic (Claude) ou Google AI (Gemini).
* [ ] Créer un fichier `.env` à la racine (ne pas commiter !).



---

## 🏗 Phase 1 : Infrastructure (The Backbone)

*Priorité : Critique | Estimation : 1 jour*

### 1.1 Stack Docker Kafka

* [ ] **Créer `infrastructure/docker-compose.yml**`
* [ ] Service: Zookeeper.
* [ ] Service: Kafka Broker (Port 9092).
* [ ] Service: Schema Registry (Port 8081).
* [ ] Service: Kafka UI (Port 8080) pour la visibilité.


* [ ] **Validation Infra**
* [ ] `docker-compose up -d` démarre sans erreur.
* [ ] Accès à Kafka UI sur `http://localhost:8080`.



### 1.2 Définition des Schémas (Avro)

* [ ] **Rédiger `schemas/habit_log_recorded.avsc**`
* [ ] Champs requis : `user_id`, `habit_id`, `timestamp`.


* [ ] **Rédiger `schemas/pattern_detected.avsc**`
* [ ] Champs : `type`, `confidence`, `payload`.


* [ ] **Rédiger `schemas/agent_command.avsc**`
* [ ] Champs : `action`, `content`, `target`.



### 1.3 Automatisation du Registre

* [ ] **Script d'init**
* [ ] Créer `infrastructure/register_schemas.py` (utilise `requests`).
* [ ] Le script doit poster les fichiers `.avsc` vers l'API du Schema Registry.
* [ ] **DoD :** Les "Subjects" apparaissent dans Kafka UI.



---

## 🔌 Phase 2 : Instrumentation Legacy (The Sensor)

*Priorité : Haute | Estimation : 1-2 jours*

### 2.1 Intégration Librairie

* [ ] Ajouter `confluent-kafka` et `fastavro` dans `requirements.txt` du backend existant.
* [ ] Installer les dépendances.

### 2.2 Module Producer

* [ ] **Créer `backend/app/events/producer.py**`
* [ ] Classe singleton `EventProducer`.
* [ ] Méthode `send_log(log_model)` qui sérialise en Avro.
* [ ] Gestion d'erreur (try/except) pour ne pas bloquer l'API si Kafka est down.



### 2.3 Hook API (FastAPI)

* [ ] **Modifier `backend/app/api/logs.py` (ou équivalent)**
* [ ] Dans le endpoint `POST /logs`, injecter l'appel `EventProducer.send_log()` après le `db.commit()`.


* [ ] **Test End-to-End manuel**
* [ ] Lancer l'app (`uvicorn`).
* [ ] Ajouter un log via le Frontend React.
* [ ] **DoD :** Voir le message apparaître dans le topic `habit.telemetry.raw` via Kafka UI.



---

## 🧠 Phase 3 : Agent Observateur (Deterministic)

*Priorité : Moyenne | Estimation : 1 jour*

### 3.1 Skeleton Agent

* [ ] Créer `agents/observer/main.py`.
* [ ] Implémenter une boucle `Consumer` basique (boucle while true).
* [ ] Configurer la désérialisation Avro automatique.

### 3.2 Logique Métier (Streak)

* [ ] **Implémenter `StreakAnalyzer**`
* [ ] Garder en mémoire (dict simple pour MVP) le dernier timestamp par `user_id`.
* [ ] Si `new_timestamp - last_timestamp > 48h`, lever une alerte.


* [ ] **Production d'Insight**
* [ ] Si alerte, publier un message Avro sur `habit.analysis.patterns`.
* [ ] **DoD :** Simuler 2 logs espacés de 3 jours et voir l'événement `PatternDetected` sortir.



---

## 🤖 Phase 4 : Agent Coach (Probabilistic / LLM)

*Priorité : Moyenne | Estimation : 2 jours*

### 4.1 Client LLM

* [ ] Créer `agents/coach/llm_client.py`.
* [ ] Intégrer LangChain ou client natif (Anthropic/Google).
* [ ] Tester un appel simple "Hello World".

### 4.2 System Prompting

* [ ] Créer `agents/coach/prompts.py`.
* [ ] Rédiger le prompt système : *"You are a stoic habit coach. Receive analysis JSON, output succinct advice."*

### 4.3 Pipeline "Think-Act"

* [ ] **Consumer Loop**
* [ ] Écouter `habit.analysis.patterns`.


* [ ] **Décision**
* [ ] Envoyer le pattern au LLM.
* [ ] Parser la réponse du LLM.


* [ ] **Action**
* [ ] Publier le résultat formaté (Avro) sur `agent.output.commands`.



---

## 📢 Phase 5 : Actuators & Bouclage

*Priorité : Basse (MVP) | Estimation : 1 jour*

### 5.1 Service de Notification (Mock)

* [ ] Créer `agents/notifier/main.py`.
* [ ] Consommer `agent.output.commands`.
* [ ] `print(f"SENDING PUSH TO {user}: {message}")`.

### 5.2 Documentation & Nettoyage

* [ ] Mettre à jour le `README.md` principal avec les commandes pour lancer tous les agents (`docker-compose` ou scripts shell).
* [ ] Faire une démo vidéo (screen record) du flux complet.

---

## 🐛 Backlog des Améliorations (Post-MVP)

* [ ] **Gestion de l'état :** Remplacer le dictionnaire mémoire de l'Observer par Redis ou Kafka Streams (KTable).
* [ ] **Sécurité :** Ajouter l'authentification SASL entre les agents et Kafka.
* [ ] **AgentOps :** Ajouter un `trace_id` qui traverse tout le chaînage pour le debugging.
# AgentMeshKafka

**Implémentation d'un Maillage Agentique (Agentic Mesh) résilient propulsé par Apache Kafka et les pratiques AgentOps.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 À propos du projet

**AgentMeshKafka** est un projet académique visant à démontrer la faisabilité et la robustesse de l'**Entreprise Agentique**. Contrairement aux approches monolithiques ou aux chatbots isolés, ce projet implémente une architecture décentralisée où des agents autonomes collaborent de manière asynchrone pour exécuter des processus métiers complexes.

Ce projet matérialise les concepts d'architecture suivants :

* **Découplage Temporel & Spatial :** Utilisation d'un backbone événementiel (Kafka) pour relier les agents.
* **AgentOps & Fiabilité :** Industrialisation des agents via des pipelines d'évaluation (Le Diamant de l'Évaluation).
* **Gouvernance des Données :** Utilisation de *Schema Registry* pour garantir des contrats de données stricts.

---

## 🏗️ Architecture du Système

L'architecture repose sur trois piliers fondamentaux, inspirés par la biologie organisationnelle :

### 1. Le Système Nerveux (Communication)

Le cœur du système n'est pas l'IA, mais le flux de données.

* **Technologie :** Apache Kafka (ou Confluent).
* **Patterns :** Event Sourcing, CQRS, Transactional Outbox.
* **Rôle :** Assure la persistance immuable des faits et la communication asynchrone entre agents.

### 2. Le Cerveau (Cognition)

Les agents sont des entités autonomes utilisant le pattern **ReAct** (Reason + Act).

* **Agent 1 (Intake) :** Réception et normalisation des demandes (Claude 3.5 Haiku).
* **Agent 2 (Analyste Risque) :** RAG (Retrieval-Augmented Generation) sur base documentaire pour évaluer le risque (Claude Opus 4.5).
* **Agent 3 (Décisionnel) :** Synthèse et exécution de l'action finale (Claude 3.5 Sonnet).

### 3. Le Système Immunitaire (Sécurité & Gouvernance)

* **AgentSec :** Validation des entrées/sorties pour prévenir les injections de prompt.
* **Data Contracts :** Schémas Avro stricts pour valider la structure des événements avant publication.

---

## 📂 Structure du Répertoire

```
AgentMeshKafka/
├── .gitignore              # Exclusion des venv, .env, __pycache__
├── docker-compose.yml      # Infrastructure Kafka/Zookeeper/Schema Registry/ChromaDB
├── requirements.txt        # Dépendances Python (LangChain, Anthropic, Kafka)
├── pytest.ini              # Configuration des tests
├── README.md               # Ce fichier
│
├── docs/                   # Documentation Architecture (DocAsCode)
│   ├── 00-Readme.md        # Index et Vision du projet
│   ├── 01-ArchitectureDecisions.md  # ADRs (5 décisions structurantes)
│   ├── 02-DataContracts.md # Schémas Avro et Topologie Kafka
│   ├── 03-AgentSpecs.md    # Personas, Outils et System Prompts
│   ├── 04-EvaluationStrategie.md  # Le "Diamant de l'Évaluation"
│   ├── 05-ThreatModel.md   # AgentSec et OWASP LLM Top 10
│   ├── 06-Plan.md          # Feuille de route (4 phases)
│   └── 07-Constitution.md  # Loi Fondamentale et Standards
│
├── schemas/                # Contrats de données Avro (.avsc)
│   ├── loan_application.avsc    # Demande de prêt
│   ├── risk_assessment.avsc     # Évaluation de risque
│   └── loan_decision.avsc       # Décision finale
│
├── scripts/                # Scripts utilitaires
│   ├── init_kafka.py       # Création des topics Kafka
│   └── register_schemas.py # Enregistrement dans Schema Registry
│
├── src/                    # Code source Python
│   ├── agents/             # Les 3 agents cognitifs
│   │   ├── intake_agent/   # Agent Intake (Claude 3.5 Haiku)
│   │   ├── risk_agent/     # Agent Risk (Claude Opus 4.5)
│   │   └── decision_agent/ # Agent Decision (Claude 3.5 Sonnet)
│   └── shared/             # Utilitaires partagés
│       ├── kafka_client.py # Wrappers Producer/Consumer
│       ├── models.py       # Modèles Pydantic (depuis Avro)
│       └── prompts.py      # System Prompts et Constitution
│
└── tests/                  # Suite de tests (Diamant de l'Évaluation)
    ├── unit/               # Niveau 1: Tests déterministes
    └── evaluation/         # Niveaux 2-4: Tests cognitifs
```

---

## 🚀 Scénario de Démonstration

Le projet simule un processus de **Traitement de Demande de Prêt Bancaire** :

1. Une demande JSON est déposée.
2. **L'Agent Intake** valide la structure et publie un événement `LoanApplicationReceived`.
3. **L'Agent Risque** consomme l'événement, consulte sa base de connaissances (politique de crédit), calcule un score et publie `RiskAssessmentCompleted`.
4. **L'Agent Décision** analyse le score, prend une décision finale (Approuvé/Refusé) et publie `LoanDecisionFinalized`.

---

## 🛠️ Installation et Démarrage

### Prérequis

* Docker & Docker Compose
* Python 3.10+
* Clé API Anthropic (Claude Opus 4.5, Claude 3.5 Sonnet/Haiku) ou accès à un LLM compatible

### 1. Lancer l'infrastructure (Système Nerveux)

```bash
docker-compose up -d
# Ceci démarre Kafka, Zookeeper et le Schema Registry
```

### 2. Initialiser l'environnement

```bash
pip install -r requirements.txt
cp .env.example .env
# Configurez votre ANTHROPIC_API_KEY dans le fichier .env
```

### 3. Initialiser Kafka et enregistrer les schémas

```bash
# Créer les topics Kafka
python scripts/init_kafka.py

# Enregistrer les schémas Avro
python scripts/register_schemas.py
```

### 4. Lancer les Agents

Dans des terminaux séparés :

```bash
# Terminal 1
python src/agents/intake_agent/main.py

# Terminal 2
python src/agents/risk_agent/main.py

# Terminal 3
python src/agents/decision_agent/main.py
```

---

## 🧪 Stratégie d'Évaluation (AgentOps)

Nous appliquons le **Diamant de l'Évaluation Agentique** pour garantir la qualité :

1. **Tests Unitaires :** Validation du code Python (connexion Kafka, parsing).
2. **Évaluation Cognitive :** Utilisation d'un LLM-Juge pour vérifier que l'Agent Risque respecte bien la politique de crédit (Factualité).
3. **Simulation :** Injection de 50 demandes variées pour observer le comportement global du maillage.

Pour lancer la suite d'évaluation :

```bash
pytest tests/evaluation/
```

Pour plus de détails, consultez [`docs/04-EvaluationStrategie.md`](docs/04-EvaluationStrategie.md).

---

## 🛡️ Sécurité (AgentSec)

* Chaque agent possède une identité propre (Service Account simulé).
* Les agents ne communiquent jamais directement entre eux (pas d'appels HTTP directs), uniquement via le Broker (Zero Trust Network).
* Filtrage des inputs pour détecter les tentatives de *Jailbreak*.
* Protection contre les injections de prompt via délimiteurs XML et validation stricte des schémas Avro.

Pour une analyse détaillée des menaces et des mesures de sécurité, consultez [`docs/05-ThreatModel.md`](docs/05-ThreatModel.md).

---

## 📚 Documentation

La documentation complète du projet est disponible dans le dossier [`docs/`](docs/) :

* **[Architecture Decisions](docs/01-ArchitectureDecisions.md)** : Justification des choix techniques (Kafka, Avro, ReAct, Event Sourcing)
* **[Data Contracts](docs/02-DataContracts.md)** : Définition des schémas Avro et topologie Kafka
* **[Agent Specifications](docs/03-AgentSpecs.md)** : Personas, outils et constitutions des agents
* **[Evaluation Strategy](docs/04-EvaluationStrategie.md)** : Méthodologie de test et validation (Diamant de l'Évaluation)
* **[Threat Model](docs/05-ThreatModel.md)** : Analyse des risques et stratégie AgentSec
* **[Plan d'Implémentation](docs/06-Plan.md)** : Feuille de route et phases de développement
* **[Constitution](docs/07-Constitution.md)** : Code de conduite, standards d'ingénierie et gouvernance cognitive

---

## 📋 Plan d'Implémentation

Le projet suit une approche itérative "Bottom-Up", organisée en 4 phases principales :

### Phase 0 : Initialisation & Environnement
Mise en place du socle technique : structure du repository, infrastructure Docker (Kafka, Zookeeper, Schema Registry), et environnement Python avec les dépendances nécessaires.

### Phase 1 : Le Système Nerveux (Data & Kafka)
Établissement des contrats d'interface stricts : définition des schémas Avro, enregistrement dans le Schema Registry, création de la topologie Kafka, et génération des classes Python.

### Phase 2 : Le Cerveau (Développement des Agents)
Implémentation de la logique cognitive des 3 agents selon le pattern ReAct :
- **Agent Intake** : Validation et normalisation des demandes
- **Base de Connaissance (RAG)** : Création de la base vectorielle et ingestion des politiques de crédit
- **Agent Risk Analyst** : Évaluation des risques avec RAG
- **Agent Loan Officer** : Prise de décision finale

### Phase 3 : Le Système Immunitaire (AgentOps & Sec)
Sécurisation et fiabilisation du maillage : tests unitaires, pipeline d'évaluation (Diamant), et implémentation des garde-fous de sécurité.

### Phase 4 : Orchestration & Démonstration
Prouver que le système fonctionne de bout en bout : script de simulation, observabilité, et rapport final.

Pour le plan détaillé avec toutes les tâches, consultez [`docs/06-Plan.md`](docs/06-Plan.md).

---

## 🎯 Décisions Architecturales Clés

### ADR-001 : Architecture Événementielle via Kafka
Adoption d'Apache Kafka comme backbone de communication asynchrone pour découpler temporellement et spatialement les agents.

### ADR-002 : Gouvernance des Données via Avro
Utilisation d'Apache Avro et Schema Registry pour garantir des contrats de données stricts et prévenir le "Schema Drift".

### ADR-003 : Pattern ReAct pour les Agents
Implémentation du pattern ReAct (Reason + Act) orchestré par LangChain/LangGraph pour permettre aux agents d'interagir avec le monde réel.

### ADR-004 : Stratégie de Résilience
Adoption d'Event Sourcing et de l'idempotence pour garantir la cohérence et l'auditabilité totale du système.

### ADR-005 : Cadre d'Évaluation Agentique
Adoption du "Diamant de l'Évaluation" combinant tests unitaires, évaluation cognitive, tests d'adversité et simulation d'écosystème.

Pour plus de détails, consultez [`docs/01-ArchitectureDecisions.md`](docs/01-ArchitectureDecisions.md).

---

## 🏛️ Constitution et Gouvernance

Le projet suit une **Constitution** définissant les principes fondamentaux et les standards d'ingénierie :

### Les Trois Lois de la Robotique Bancaire

1. **Intégrité du Contrat (Schema First)** : Un agent ne doit jamais émettre un événement qui viole le schéma Avro défini.
2. **Transparence Cognitive (Chain of Thought)** : Un agent doit toujours expliciter son raisonnement interne avant de produire une action.
3. **Sécurité et Confidentialité (AgentSec)** : Un agent doit protéger ses instructions internes contre les injections de prompt et sanitiser les données personnelles.

### Stack Technologique

Le projet utilise la suite **Anthropic nouvelle génération** :
- **Claude Opus 4.5** : Moteur cognitif principal pour les tâches critiques (Agent Risk Analyst)
- **Claude Code** : Assistant de développement pour la génération de code et le refactoring
- **Auto Claude** : AgentOps et auto-correction pour la surveillance et l'amélioration continue

Pour les détails complets sur la Constitution, les protocoles de développement et la matrice de responsabilité des modèles, consultez [`docs/07-Constitution.md`](docs/07-Constitution.md).

---

## 👥 Auteurs et Références

Projet réalisé dans le cadre académique sur l'architecture des systèmes agentiques.

* **Basé sur les travaux de :** André-Guy Bruneau (Architecture – Maillage Agentique et AgentOps).
* **Licence :** MIT.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour toute question ou suggestion, veuillez ouvrir une issue.

---

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

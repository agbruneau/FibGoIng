# AgentMeshKafka

**Implémentation d'un Maillage Agentique (Agentic Mesh) résilient propulsé par Apache Kafka et les pratiques AgentOps.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 À propos du projet

**AgentMeshKafka** est un projet académique visant à démontrer la faisabilité et la robustesse de l'**Entreprise Agentique**. Contrairement aux approches monolithiques ou aux chatbots isolés, ce projet implémente une architecture décentralisée où des agents autonomes collaborent de manière asynchrone pour exécuter des processus métiers complexes.

Ce projet suit une **approche progressive** organisée en 5 phases, permettant un apprentissage et une démonstration incrémentale :

- **Phase 0** : MVP fonctionnel sans infrastructure (démarrage en 5 minutes)
- **Phase 1** : Ajout de Kafka pour la communication événementielle
- **Phase 2** : Intégration RAG avec ChromaDB
- **Phase 3** : Tests et évaluation complète
- **Phase 4** : Version avancée avec Schema Registry et monitoring

---

## 🚀 Démarrage Rapide

### Pour commencer immédiatement (Phase 0)

```bash
cd phase0
pip install -r requirements.txt
python main.py
```

**Temps estimé :** < 5 minutes | **Prérequis :** Python 3.10+, clé API Anthropic

👉 Consultez [QUICKSTART.md](QUICKSTART.md) pour un guide détaillé.

### Pour une progression complète

Consultez [PHASES.md](PHASES.md) pour comprendre comment passer d'une phase à l'autre.

---

## 📂 Structure du Projet

```
AgentMeshKafka/
├── README.md              # Ce fichier
├── QUICKSTART.md         # Guide de démarrage rapide (Phase 0)
├── PHASES.md             # Guide de progression entre phases
│
├── phase0/               # MVP - Agents simples sans infrastructure
├── phase1/               # + Kafka (KRaft, sans Zookeeper)
├── phase2/               # + RAG ChromaDB
├── phase3/               # + Tests complets
├── phase4/               # Version complète (Schema Registry, monitoring)
│
├── docs/                 # Documentation technique
├── notebooks/            # Tutoriels Jupyter interactifs
└── examples/             # Scripts d'exemple progressifs
```

---

## 🎯 Choisir une Phase

| Phase | Complexité | Temps Setup | Idéal pour |
|-------|-----------|-------------|------------|
| **Phase 0** | ⭐ Très simple | < 5 min | Démonstration rapide, apprentissage des agents |
| **Phase 1** | ⭐⭐ Simple | ~15 min | Comprendre Kafka et événements |
| **Phase 2** | ⭐⭐⭐ Modéré | ~20 min | Découvrir RAG et bases vectorielles |
| **Phase 3** | ⭐⭐⭐ Modéré | ~10 min | Tests et validation |
| **Phase 4** | ⭐⭐⭐⭐ Avancé | ~30 min | Production-ready, gouvernance complète |

### Recommandations

- **Projet d'école (2-3 mois)** : Phase 0-2
- **Projet d'étudiant (3-6 mois)** : Phase 1-3
- **Thèse/projet long (9-12 mois)** : Phase 0-4 complète
- **Démonstration uniquement** : Phase 0

---

## 🏗️ Architecture du Système

L'architecture repose sur trois piliers fondamentaux, inspirés par la biologie organisationnelle :

### 1. Le Système Nerveux (Communication)

Le cœur du système n'est pas l'IA, mais le flux de données.

* **Technologie :** Apache Kafka (à partir de Phase 1)
* **Patterns :** Event Sourcing, CQRS, Transactional Outbox
* **Rôle :** Assure la persistance immuable des faits et la communication asynchrone entre agents

### 2. Le Cerveau (Cognition)

Les agents sont des entités autonomes utilisant le pattern **ReAct** (Reason + Act).

* **Agent 1 (Intake) :** Réception et normalisation des demandes (Claude 3.5 Haiku)
* **Agent 2 (Analyste Risque) :** RAG sur base documentaire pour évaluer le risque (Claude Opus 4.5)
* **Agent 3 (Décisionnel) :** Synthèse et exécution de l'action finale (Claude 3.5 Sonnet)

### 3. Le Système Immunitaire (Sécurité & Gouvernance)

* **AgentSec :** Validation des entrées/sorties pour prévenir les injections de prompt
* **Data Contracts :** Schémas Avro stricts (Phase 4) pour valider la structure des événements

---

## 🚀 Scénario de Démonstration

Le projet simule un processus de **Traitement de Demande de Prêt Bancaire** :

1. Une demande JSON est déposée
2. **L'Agent Intake** valide la structure et publie un événement `LoanApplicationReceived`
3. **L'Agent Risque** consomme l'événement, consulte sa base de connaissances (politique de crédit), calcule un score et publie `RiskAssessmentCompleted`
4. **L'Agent Décision** analyse le score, prend une décision finale (Approuvé/Refusé) et publie `LoanDecisionFinalized`

---

## 📚 Documentation

### Guides Essentiels

- **[QUICKSTART.md](QUICKSTART.md)** : Démarrage rapide Phase 0 (< 5 minutes)
- **[PHASES.md](PHASES.md)** : Guide détaillé de progression entre phases

### Documentation Technique

La documentation complète est disponible dans [`docs/`](docs/) :

* **[Architecture](docs/01-Architecture.md)** : Vue d'ensemble et décisions architecturales
* **[Data Contracts](docs/02-DataContracts.md)** : Schémas et topologie Kafka (Phase 4)
* **[Agent Specifications](docs/03-AgentSpecs.md)** : Personas, outils et prompts des agents
* **[Setup Guide](docs/04-Setup.md)** : Instructions d'installation par phase

### Ressources Pédagogiques

* **[Notebooks Jupyter](notebooks/)** : Tutoriels interactifs
  - `01-agents-intro.ipynb` : Introduction aux agents
  - `02-rag-demo.ipynb` : Démonstration RAG
  - `03-kafka-flow.ipynb` : Flux Kafka visualisé

* **[Exemples](examples/)** : Scripts progressifs
  - `01-simple-agent.py` : Agent minimal
  - `02-agent-with-kafka.py` : Avec messaging
  - `03-full-flow.py` : Pipeline complet

---

## 🛠️ Prérequis

### Commun à toutes les phases

* Python 3.10+
* Clé API Anthropic (Claude Opus 4.5, Claude 3.5 Sonnet/Haiku) ou accès à un LLM compatible

### Par phase

* **Phase 0** : Aucun prérequis supplémentaire
* **Phase 1+** : Docker & Docker Compose
* **Phase 2+** : Espace disque pour ChromaDB (~500MB)
* **Phase 4** : Connaissance de Schema Registry (optionnel)

---

## 🧪 Stratégie d'Évaluation (AgentOps)

À partir de la Phase 3, nous appliquons le **Diamant de l'Évaluation Agentique** :

1. **Tests Unitaires (L1)** : Validation du code Python
2. **Évaluation Cognitive (L2)** : Utilisation d'un LLM-Juge pour vérifier la factualité
3. **Tests d'Adversité (L3)** : Injection de prompts malveillants
4. **Simulation d'Écosystème (L4)** : Injection de 50 demandes variées

---

## 🛡️ Sécurité (AgentSec)

* Chaque agent possède une identité propre (Service Account simulé)
* Les agents ne communiquent jamais directement entre eux (pas d'appels HTTP directs), uniquement via le Broker (Zero Trust Network)
* Filtrage des inputs pour détecter les tentatives de *Jailbreak*
* Protection contre les injections de prompt via délimiteurs XML et validation stricte des schémas (Phase 4)

---

## 🎯 Décisions Architecturales Clés

### ADR-001 : Architecture Événementielle via Kafka
Adoption d'Apache Kafka comme backbone de communication asynchrone pour découpler temporellement et spatialement les agents.

### ADR-002 : Gouvernance des Données via Avro
Utilisation d'Apache Avro et Schema Registry (Phase 4) pour garantir des contrats de données stricts.

### ADR-003 : Pattern ReAct pour les Agents
Implémentation du pattern ReAct (Reason + Act) orchestré par LangChain/LangGraph.

Pour plus de détails, consultez [`docs/01-Architecture.md`](docs/01-Architecture.md).

---

## 👥 Auteurs et Références

Projet réalisé dans le cadre académique sur l'architecture des systèmes agentiques.

* **Basé sur les travaux de :** André-Guy Bruneau (Architecture – Maillage Agentique et AgentOps)
* **Licence :** MIT

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour toute question ou suggestion, veuillez ouvrir une issue.

---

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

# Phase 4 : Version Avancée Complète

**Complexité :** ⭐⭐⭐⭐ Avancé | **Temps setup :** ~30 minutes

La Phase 4 est la version **production-ready** complète avec :
- Schema Registry (gouvernance des données Avro)
- Monitoring (Control Center optionnel)
- Évaluation complète (L1-L4)
- Observabilité (OpenTelemetry)

---

## 🎯 Objectif

Version complète avec toutes les fonctionnalités :
- Gouvernance des données via Schema Registry
- Schémas Avro complets avec versioning
- Monitoring et observabilité
- Tests complets (L1-L4)

---

## 📋 Prérequis

- Docker & Docker Compose
- Python 3.10+
- Clé API Anthropic
- Connaissance de Schema Registry (recommandé)

---

## ⚡ Installation Rapide

```bash
# 1. Démarrer toute l'infrastructure
docker-compose up -d

# Attendre que tous les services soient prêts (~2 minutes)
# Vérifier: docker-compose ps

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Créer les topics Kafka
python scripts/init_kafka.py

# 4. Enregistrer les schémas Avro dans Schema Registry
python scripts/register_schemas.py

# 5. Ingérer les documents de politique (si RAG activé)
python scripts/ingest_policies.py  # Si disponible

# 6. Lancer les agents (dans des terminaux séparés)
python src/agents/intake_agent/main.py
python src/agents/risk_agent/main.py
python src/agents/decision_agent/main.py
```

---

## 📂 Structure

```
phase4/
├── README.md              # Ce fichier
├── docker-compose.yml     # Stack complète (Kafka, Zookeeper, Schema Registry, ChromaDB)
├── requirements.txt       # Toutes les dépendances
├── schemas/               # Schémas Avro (.avsc)
├── scripts/               # Scripts d'initialisation
├── src/                   # Code source complet
└── tests/                 # Tests complets (L1-L4)
```

---

## 🔍 Différences avec Phase 3

| Aspect | Phase 3 | Phase 4 |
|--------|---------|---------|
| Schémas | JSON/Pydantic | Avro + Schema Registry |
| Validation | Runtime | Schema Registry |
| Monitoring | Logs | Control Center |
| Tests | L1-L2 | L1-L4 complet |
| Observabilité | Basique | OpenTelemetry |

---

## 🏗️ Infrastructure Complète

### Services Docker

- **Zookeeper** : Coordination (ou KRaft en production)
- **Kafka** : Broker événementiel
- **Schema Registry** : Gouvernance des schémas Avro
- **ChromaDB** : Base vectorielle pour RAG
- **Control Center** : Monitoring (optionnel, avec `--profile monitoring`)

### Schémas Avro

Les schémas sont définis dans `schemas/` :
- `loan_application.avsc`
- `risk_assessment.avsc`
- `loan_decision.avsc`

Ils sont enregistrés dans le Schema Registry avec compatibilité FORWARD.

---

## 🧪 Tests Complets

### L1 - Tests Unitaires

```bash
pytest tests/unit/ -v
```

### L2 - Évaluation Cognitive

```bash
pytest tests/evaluation/ -v
```

### L3 - Tests d'Adversité (si implémentés)

```bash
pytest tests/adversarial/ -v
```

### L4 - Simulation d'Écosystème (si implémentés)

```bash
pytest tests/simulation/ -v
```

---

## 📊 Monitoring

### Control Center

Accédez à l'interface de monitoring :

```bash
docker-compose --profile monitoring up -d
# Puis ouvrez http://localhost:9021
```

### Logs Structurés

Les agents utilisent `structlog` pour des logs structurés avec trace_id.

---

## 🔧 Configuration Avancée

### Variables d'Environnement

Créez un fichier `.env` :

```bash
ANTHROPIC_API_KEY=votre_clé
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### Modèles LLM

Configurez les modèles par agent dans `.env` :

```bash
INTAKE_AGENT_MODEL=claude-3-5-haiku-20241022
RISK_AGENT_MODEL=claude-sonnet-4-20250514
DECISION_AGENT_MODEL=claude-3-5-sonnet-20241022
```

---

## 🐛 Dépannage

**Schema Registry ne démarre pas**
- Vérifiez que Kafka est prêt: `docker-compose logs kafka`
- Vérifiez les logs: `docker-compose logs schema-registry`

**Erreur "Schema not found"**
- Enregistrez les schémas: `python scripts/register_schemas.py`

**Control Center inaccessible**
- Vérifiez le profile: `docker-compose --profile monitoring ps`

---

## 📚 Documentation Complète

Consultez la documentation dans `../docs/` :
- [Architecture Decisions](../docs/01-Architecture.md)
- [Data Contracts](../docs/02-DataContracts.md)
- [Agent Specifications](../docs/03-AgentSpecs.md)

---

## 💡 Production

Pour un déploiement en production :

1. Utilisez Kafka KRaft (sans Zookeeper)
2. Configurez la réplication (3+ brokers)
3. Activez le monitoring complet
4. Configurez les alertes
5. Utilisez des schémas Avro stricts

---

**Besoin d'aide ?** Consultez [../PHASES.md](../PHASES.md) ou la documentation complète.

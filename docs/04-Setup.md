# Guide d'Installation par Phase

> **Version :** 2.0.0 | **Statut :** Simplifié | **Dernière révision :** Janvier 2026

Ce document fournit les instructions d'installation pour chaque phase du projet.

---

## Phase 0 : MVP Fonctionnel

**Prérequis :** Python 3.10+, clé API Anthropic

```bash
cd phase0
pip install -r requirements.txt
# Créer .env avec ANTHROPIC_API_KEY
python main.py
```

**Temps :** < 5 minutes

**Détails :** Consultez [../QUICKSTART.md](../QUICKSTART.md)

---

## Phase 1 : Kafka

**Prérequis :** Docker, Python 3.10+, clé API Anthropic

```bash
cd phase1
docker-compose up -d
pip install -r requirements.txt
python scripts/init_kafka.py
# Lancer les agents dans des terminaux séparés
```

**Temps :** ~15 minutes

**Détails :** Consultez `phase1/README.md`

---

## Phase 2 : RAG

**Prérequis :** Docker, Python 3.10+, clé API Anthropic

```bash
cd phase2
docker-compose up -d
pip install -r requirements.txt
python scripts/init_kafka.py
python scripts/ingest_policies.py
# Lancer les agents
```

**Temps :** ~20 minutes

**Détails :** Consultez `phase2/README.md`

---

## Phase 3 : Tests

**Prérequis :** Phase 2 complétée

```bash
cd phase3
# Infrastructure identique à Phase 2
docker-compose up -d
pip install -r requirements.txt
pytest tests/unit/ -v
pytest tests/evaluation/ -v
```

**Temps :** ~10 minutes

**Détails :** Consultez `phase3/README.md`

---

## Phase 4 : Version Complète

**Prérequis :** Docker, Python 3.10+, clé API Anthropic, connaissance Schema Registry

```bash
cd phase4
docker-compose up -d
pip install -r requirements.txt
python scripts/init_kafka.py
python scripts/register_schemas.py
# Lancer les agents
```

**Temps :** ~30 minutes

**Détails :** Consultez `phase4/README.md`

---

## Problèmes Courants

**Kafka ne démarre pas :** Vérifiez les logs avec `docker-compose logs kafka`

**Erreur "Module not found" :** Réinstallez avec `pip install -r requirements.txt --force-reinstall`

**Schema Registry inaccessible :** Vérifiez que Kafka est prêt avant de démarrer Schema Registry

---

**Pour plus d'aide :** Consultez [../PHASES.md](../PHASES.md) ou les README de chaque phase.

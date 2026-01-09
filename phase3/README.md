# Phase 3 : Tests et Validation

**Complexité :** ⭐⭐⭐ Modéré | **Temps setup :** ~10 minutes

La Phase 3 ajoute une suite de tests complète pour valider le système :
- Tests unitaires (L1) : Validation déterministe
- Tests cognitifs (L2) : Validation par LLM-Juge

---

## 🎯 Objectif

Comprendre la validation des agents :
- Tests unitaires pour les outils et modèles
- Tests d'intégration end-to-end
- Évaluation cognitive (LLM-as-a-Judge)
- Pipeline de validation

---

## 📋 Prérequis

- Docker & Docker Compose
- Python 3.10+
- Clé API Anthropic
- Phase 2 maîtrisée (recommandé)

---

## ⚡ Installation Rapide

```bash
# 1. Démarrer l'infrastructure (identique à Phase 2)
docker-compose up -d

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Créer les topics Kafka
python scripts/init_kafka.py

# 4. Ingérer les documents de politique
python scripts/ingest_policies.py

# 5. Lancer les tests
pytest tests/unit/ -v
pytest tests/evaluation/ -v
```

---

## 📂 Structure

```
phase3/
├── README.md              # Ce fichier
├── pytest.ini            # Configuration pytest
├── tests/
│   ├── unit/             # Tests unitaires (L1)
│   │   ├── test_models.py
│   │   └── test_tools.py
│   └── evaluation/       # Tests cognitifs (L2)
│       └── test_risk_agent_cognitive.py
└── ...                    # Code de Phase 2
```

---

## 🧪 Niveaux de Test

### L1 - Tests Unitaires

Tests déterministes pour :
- Validation des modèles Pydantic
- Calculs mathématiques (DTI, scores)
- Outils des agents

```bash
pytest tests/unit/test_models.py -v
pytest tests/unit/test_tools.py -v
```

### L2 - Évaluation Cognitive

Tests utilisant un LLM-Juge pour valider :
- Factualité des réponses
- Conformité aux politiques
- Qualité de la justification

```bash
pytest tests/evaluation/test_risk_agent_cognitive.py -v
```

---

## 🔍 Exemples de Tests

### Test Unitaire (L1)

```python
def test_calculate_dti():
    """Test du calcul du ratio dette/revenu."""
    dti = calculate_debt_ratio(income=5000, debts=1000, loan=50000)
    assert dti == 20.0  # (1000 + 500) / 5000 * 100
```

### Test Cognitif (L2)

```python
def test_risk_agent_respects_policy():
    """Test que l'agent respecte les politiques."""
    assessment = risk_agent.analyze(application)
    
    # LLM-Juge évalue la réponse
    judge = LLMJudge()
    score = judge.evaluate(
        response=assessment.rationale,
        reference=policy_document,
        criteria=["factuality", "conformity"]
    )
    
    assert score["factuality"] >= 8.0
```

---

## 📊 Résultats des Tests

Les tests génèrent un rapport avec :
- Taux de réussite
- Scores de factualité
- Temps d'exécution
- Détails des échecs

---

## 🐛 Dépannage

**Tests échouent avec "Module not found"**
- Vérifiez que vous êtes dans le répertoire phase3/
- Réinstallez: `pip install -r requirements.txt`

**Tests cognitifs coûteux**
- Limitez le nombre de tests: `pytest tests/evaluation/ -k "test_specific"`

**Timeout sur les tests**
- Augmentez le timeout dans `pytest.ini`

---

## 📚 Prochaines étapes

Une fois que vous maîtrisez la Phase 3 :

1. **Phase 4** : Version avancée complète
   - Consultez [../PHASES.md](../PHASES.md)
   - Naviguez vers `phase4/`

---

**Besoin d'aide ?** Consultez [../PHASES.md](../PHASES.md) ou la documentation pytest.

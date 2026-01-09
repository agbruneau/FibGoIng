# Phase 0 : MVP Fonctionnel

**Complexité :** ⭐ Très simple | **Temps setup :** < 5 minutes

La Phase 0 est la version la plus simple d'AgentMeshKafka. Elle permet de comprendre le fonctionnement des agents **sans aucune infrastructure** (pas de Docker, pas de Kafka).

---

## 🎯 Objectif

Comprendre comment trois agents LLM collaborent pour traiter une demande de prêt :
1. **Agent Intake** : Valide la demande
2. **Agent Risk** : Calcule un score de risque
3. **Agent Decision** : Prend la décision finale

---

## 📋 Prérequis

- Python 3.10+
- Clé API Anthropic
- `pip` installé

---

## ⚡ Installation Rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer la clé API
# Créez un fichier .env avec:
# ANTHROPIC_API_KEY=votre_clé_ici

# 3. Exécuter
python main.py
```

---

## 📂 Structure

```
phase0/
├── README.md           # Ce fichier
├── requirements.txt    # Dépendances minimales
├── main.py            # Script orchestrateur
├── models.py          # Modèles de données (Pydantic)
└── agents/
    ├── intake.py      # Agent de validation
    ├── risk.py        # Agent d'évaluation de risque
    └── decision.py    # Agent de décision
```

---

## 🔍 Comment ça fonctionne

### Flux de traitement

```python
# 1. Agent Intake valide la demande
validated = IntakeAgent().process(request)

# 2. Agent Risk calcule le score
assessment = RiskAgent().analyze(validated)

# 3. Agent Decision prend la décision
decision = DecisionAgent().decide(assessment)
```

### Exemple de sortie

```
✅ Demande validée: CUST-12345
📊 Score de risque: 45/100 (MEDIUM)
✅ Décision: APPROVED - Montant approuvé: 50000.0 USD
```

---

## 🧪 Tester avec vos données

Modifiez `main.py` pour tester avec vos propres données :

```python
request = {
    "applicant_id": "CUST-99999",
    "amount_requested": 75000,
    "currency": "USD",
    "declared_monthly_income": 6000,
    "employment_status": "FULL_TIME",
    "existing_debts": 5000,
    "loan_purpose": "Achat immobilier"
}
```

---

## 💡 Différences avec les autres phases

| Aspect | Phase 0 | Phase 1+ |
|--------|---------|----------|
| Communication | Appels directs | Événements Kafka |
| Infrastructure | Aucune | Docker requis |
| Déploiement | Script unique | Processus séparés |
| Complexité | ⭐ | ⭐⭐+ |

---

## 📚 Prochaines étapes

Une fois que vous maîtrisez la Phase 0 :

1. **Phase 1** : Ajouter Kafka pour la communication asynchrone
   - Consultez [../PHASES.md](../PHASES.md)
   - Naviguez vers `phase1/`

2. **Explorer les notebooks** :
   - `../notebooks/01-agents-intro.ipynb`

3. **Consulter les exemples** :
   - `../examples/01-simple-agent.py`

---

## 🐛 Dépannage

**Erreur : "ANTHROPIC_API_KEY not found"**
- Vérifiez que le fichier `.env` existe et contient votre clé

**Erreur : "Module not found"**
- Réinstallez : `pip install -r requirements.txt --force-reinstall`

---

## 💰 Coûts

Environ **$0.01-0.05** par exécution (3 appels API Anthropic).

---

**Besoin d'aide ?** Consultez [../QUICKSTART.md](../QUICKSTART.md) ou [../PHASES.md](../PHASES.md).

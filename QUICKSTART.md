# 🚀 Guide de Démarrage Rapide - Phase 0

**Temps estimé :** < 5 minutes | **Complexité :** ⭐ Très simple

Ce guide vous permet de démarrer avec AgentMeshKafka en utilisant la **Phase 0** (MVP sans infrastructure). C'est la façon la plus rapide de comprendre le fonctionnement des agents.

---

## 📋 Prérequis

- Python 3.10 ou supérieur
- Clé API Anthropic (Claude)
- `pip` installé

### Vérifier Python

```bash
python --version
# Doit afficher Python 3.10.x ou supérieur
```

---

## ⚡ Installation en 3 Étapes

### 1. Naviguer vers la Phase 0

```bash
cd phase0
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Dépendances installées :**
- `anthropic` : SDK Anthropic pour Claude
- `pydantic` : Validation de données
- `python-dotenv` : Gestion des variables d'environnement

### 3. Configurer votre clé API

Créez un fichier `.env` dans le dossier `phase0/` :

```bash
# phase0/.env
ANTHROPIC_API_KEY=votre_clé_api_ici
```

**Où obtenir une clé API :**
1. Allez sur [console.anthropic.com](https://console.anthropic.com)
2. Créez un compte ou connectez-vous
3. Générez une clé API dans la section "API Keys"

---

## 🎯 Exécuter votre Premier Agent

### Exécution Simple

```bash
python main.py
```

**Ce qui se passe :**
1. L'Agent Intake valide une demande de prêt exemple
2. L'Agent Risk calcule un score de risque
3. L'Agent Decision prend une décision finale
4. Le résultat s'affiche dans la console

### Exemple de Sortie

```
✅ Demande validée: CUST-12345
📊 Score de risque: 45/100 (MEDIUM)
✅ Décision: APPROVED - Montant approuvé: 50000.0 USD
```

---

## 🔍 Comprendre le Code

### Structure de Phase 0

```
phase0/
├── main.py              # Script orchestrateur
├── agents/
│   ├── intake.py       # Agent de validation
│   ├── risk.py         # Agent d'évaluation de risque
│   └── decision.py     # Agent de décision
└── models.py           # Modèles de données (Pydantic)
```

### Flux de Traitement

```python
# 1. Agent Intake valide la demande
validated = IntakeAgent().process(request)

# 2. Agent Risk calcule le score
assessment = RiskAgent().analyze(validated)

# 3. Agent Decision prend la décision
decision = DecisionAgent().decide(assessment)
```

---

## 🧪 Tester avec vos Propres Données

Modifiez `main.py` pour tester avec vos propres données :

```python
# Exemple de demande personnalisée
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

## 🐛 Dépannage

### Erreur : "ANTHROPIC_API_KEY not found"

**Solution :** Vérifiez que le fichier `.env` existe dans `phase0/` et contient votre clé API.

### Erreur : "Module not found"

**Solution :** Réinstallez les dépendances :
```bash
pip install -r requirements.txt --force-reinstall
```

### Erreur : "Rate limit exceeded"

**Solution :** Vous avez atteint la limite d'appels API. Attendez quelques minutes ou vérifiez votre plan Anthropic.

---

## 📚 Prochaines Étapes

Une fois que vous maîtrisez la Phase 0 :

1. **Phase 1** : Ajouter Kafka pour la communication événementielle
   - Consultez [PHASES.md](../PHASES.md) pour la transition
   - Naviguez vers `phase1/` et suivez son README

2. **Explorer les Notebooks** : 
   - Ouvrez `notebooks/01-agents-intro.ipynb` pour une démonstration interactive

3. **Consulter les Exemples** :
   - Regardez `examples/01-simple-agent.py` pour un exemple minimal

---

## 💡 Conseils

- **Pour une démo rapide** : La Phase 0 est parfaite, elle fonctionne sans Docker
- **Pour comprendre Kafka** : Passez à la Phase 1
- **Pour voir le RAG en action** : Passez à la Phase 2

---

## ❓ Questions Fréquentes

**Q : Puis-je utiliser OpenAI au lieu d'Anthropic ?**  
R : Oui, mais vous devrez modifier le code des agents pour utiliser le SDK OpenAI. La Phase 0 est conçue pour Anthropic.

**Q : Combien coûte l'exécution de la Phase 0 ?**  
R : Environ $0.01-0.05 par exécution (3 appels API Anthropic). Très économique pour tester.

**Q : Puis-je déployer la Phase 0 en production ?**  
R : Non, la Phase 0 est un MVP pédagogique. Pour la production, utilisez la Phase 4.

---

## 🎓 Ressources d'Apprentissage

- [Documentation Anthropic](https://docs.anthropic.com)
- [Guide LangChain](https://python.langchain.com)
- [Notre documentation](../docs/)

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub ou consultez [PHASES.md](../PHASES.md) pour plus de détails.

# Phase 2 : RAG avec ChromaDB

**Complexité :** ⭐⭐⭐ Modéré | **Temps setup :** ~20 minutes

La Phase 2 ajoute **RAG (Retrieval-Augmented Generation)** avec ChromaDB pour enrichir l'Agent Risk avec une base de connaissances sur les politiques de crédit.

---

## 🎯 Objectif

Comprendre le RAG :
- Bases vectorielles (ChromaDB)
- Embeddings et recherche sémantique
- Enrichissement contextuel des agents
- Amélioration de la précision des évaluations

---

## 📋 Prérequis

- Docker & Docker Compose
- Python 3.10+
- Clé API Anthropic
- Phase 1 maîtrisée (recommandé)

---

## ⚡ Installation Rapide

```bash
# 1. Démarrer Kafka + ChromaDB
docker-compose up -d

# Attendre que les services soient prêts (~1 minute)
# Vérifier: docker-compose ps

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Créer les topics Kafka
python scripts/init_kafka.py

# 4. Ingérer les documents de politique dans ChromaDB
python scripts/ingest_policies.py

# 5. Lancer les agents (dans des terminaux séparés)
# Terminal 1
python src/agents/intake_agent/main.py

# Terminal 2
python src/agents/risk_agent/main.py  # Maintenant avec RAG!

# Terminal 3
python src/agents/decision_agent/main.py
```

---

## 📂 Structure

```
phase2/
├── README.md              # Ce fichier
├── docker-compose.yml     # Kafka + ChromaDB
├── requirements.txt       # + chromadb, sentence-transformers
├── data/
│   └── credit_policy.md  # Document de politique de crédit
├── scripts/
│   ├── init_kafka.py
│   └── ingest_policies.py  # Ingestion dans ChromaDB
└── src/
    ├── agents/
    │   └── risk_agent/
    │       └── main.py    # Avec RAG intégré
    └── shared/
        └── rag_client.py  # Client ChromaDB
```

---

## 🔍 Différences avec Phase 1

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Agent Risk | Calculs simples | RAG + Politiques |
| Base de données | Aucune | ChromaDB |
| Contexte | Limité | Enrichi par RAG |
| Précision | Basique | Améliorée |

---

## 🧠 Comment fonctionne le RAG

1. **Ingestion** : Les documents de politique sont chunkés et vectorisés
2. **Stockage** : Les embeddings sont stockés dans ChromaDB
3. **Recherche** : L'Agent Risk interroge ChromaDB avec une requête sémantique
4. **Enrichissement** : Les documents pertinents sont injectés dans le prompt LLM

---

## 🧪 Tester le RAG

### 1. Vérifier l'ingestion

```bash
python scripts/ingest_policies.py
# Doit afficher: ✅ Documents ingérés avec succès
```

### 2. Tester une recherche

```python
from src.shared.rag_client import RAGClient

client = RAGClient()
results = client.search("règles pour travailleurs indépendants")
print(results)
```

### 3. Observer les logs

L'Agent Risk affiche maintenant les politiques consultées :
```
📚 Politiques consultées: Policy-4.2-SelfEmployed, Policy-2.1-DTI-Limits
```

---

## 📚 Documents de Politique

Le fichier `data/credit_policy.md` contient les règles de crédit. Vous pouvez :
- Modifier ce fichier pour tester différents scénarios
- Ajouter d'autres documents dans `data/`
- Ré-ingérer après modification : `python scripts/ingest_policies.py`

---

## 🐛 Dépannage

**ChromaDB ne démarre pas**
- Vérifiez les logs: `docker-compose logs chromadb`
- Assurez-vous que le port 8000 n'est pas utilisé

**Erreur "Collection not found"**
- Ré-ingérez les documents: `python scripts/ingest_policies.py`

**Recherche ne retourne rien**
- Vérifiez que les documents sont bien ingérés
- Testez avec une requête plus générale

---

## 📚 Prochaines étapes

Une fois que vous maîtrisez la Phase 2 :

1. **Phase 3** : Ajouter les tests
   - Consultez [../PHASES.md](../PHASES.md)
   - Naviguez vers `phase3/`

2. **Explorer les notebooks** :
   - `../notebooks/02-rag-demo.ipynb`

---

## 💡 Concepts Clés

- **Embedding** : Représentation vectorielle d'un texte
- **Similarité cosinus** : Mesure de similarité entre vecteurs
- **Chunking** : Découpage de documents en morceaux
- **Retrieval** : Recherche de documents pertinents

---

**Besoin d'aide ?** Consultez [../PHASES.md](../PHASES.md) ou les logs Docker.

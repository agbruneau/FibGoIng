# Spécifications des Agents

> **Version :** 2.0.0 | **Statut :** Simplifié | **Dernière révision :** Janvier 2026

Ce document présente les **spécifications simplifiées** des 3 agents du système. Pour les détails complets, consultez `phase4/docs/03-AgentSpecs.md`.

---

## Agent 1 : Intake Specialist

**Rôle :** Validation et normalisation des demandes de prêt.

**Entrées :** Demande brute (JSON)

**Sorties :** Événement `LoanApplication` dans Kafka

**Outils :**
- Validation de format
- Conversion de devise
- Validation sémantique via LLM

**Modèle :** Claude 3.5 Haiku (rapide, économique)

---

## Agent 2 : Risk Analyst

**Rôle :** Évaluation de risque avec RAG sur les politiques de crédit.

**Entrées :** Événement `LoanApplication` depuis Kafka

**Sorties :** Événement `RiskAssessment` dans Kafka

**Outils :**
- `search_credit_policy` : RAG dans ChromaDB
- `calculate_debt_ratio` : Calcul DTI
- `fetch_credit_history` : Historique simulé

**Modèle :** Claude 3.5 Sonnet / Opus 4.5 (raisonnement complexe)

**Note :** RAG disponible à partir de la Phase 2.

---

## Agent 3 : Loan Officer

**Rôle :** Décision finale d'approbation ou rejet.

**Entrées :** Événement `RiskAssessment` depuis Kafka

**Sorties :** Événement `LoanDecision` dans Kafka

**Critères :**
- Score < 20 : Approbation automatique
- Score > 80 : Rejet automatique
- Entre 20-80 : Analyse détaillée

**Modèle :** Claude 3.5 Sonnet (décision finale)

---

## Pattern ReAct

Tous les agents suivent le pattern ReAct :

1. **Thought** : Analyse
2. **Action** : Utilisation d'un outil
3. **Observation** : Résultat
4. **Final Answer** : Synthèse

---

**Pour plus de détails :** Consultez `phase4/docs/03-AgentSpecs.md` pour les spécifications complètes avec prompts détaillés.

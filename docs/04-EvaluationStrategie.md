# Stratégie d'Évaluation (Simplifiée)

> **Version :** 2.0.0 | **Statut :** Simplifié | **Dernière révision :** Janvier 2026

Ce document présente une **version simplifiée** de la stratégie d'évaluation. Pour les détails complets, consultez `phase4/docs/04-EvaluationStrategie.md`.

---

## Le Diamant de l'Évaluation

Le système utilise 4 niveaux d'évaluation, du plus simple au plus complexe :

### Niveau 1 : Tests Unitaires (L1)

**Objectif :** Valider le code Python déterministe.

**Exemples :**
- Validation des modèles Pydantic
- Calculs mathématiques (DTI, scores)
- Parsing Avro

**Outils :** `pytest`

**Disponible :** Phase 3+

---

### Niveau 2 : Évaluation Cognitive (L2)

**Objectif :** Valider le raisonnement des agents via LLM-Juge.

**Méthodologie :** Un LLM "Juge" évalue les réponses des agents selon :
- **Factualité** : La réponse est-elle supportée par les documents ?
- **Conformité** : Le format est-il respecté ?
- **Sécurité** : Pas de fuite d'information

**Outils :** `pytest` + LLM-Juge (Claude)

**Disponible :** Phase 3+

---

### Niveau 3 : Tests d'Adversité (L3)

**Objectif :** Tester la résistance aux attaques (Prompt Injection, etc.)

**Scénarios :**
- Tentative de manipulation des prompts
- Injection de données malveillantes
- Tests de robustesse

**Disponible :** Phase 4 (optionnel)

---

### Niveau 4 : Simulation d'Écosystème (L4)

**Objectif :** Observer le comportement global du système.

**Méthodologie :** Injection de 50+ demandes variées et observation des métriques :
- Taux de succès
- Latence
- Coûts

**Disponible :** Phase 4 (optionnel)

---

## Exemple de Test Cognitif

```python
def test_risk_agent_respects_policy():
    """Test que l'agent cite les politiques."""
    assessment = risk_agent.analyze(application)
    
    judge = LLMJudge()
    score = judge.evaluate(
        response=assessment.rationale,
        reference=policy_document
    )
    
    assert score["factuality"] >= 7.0
```

---

## Recommandations

- **Phase 3 :** Focus sur L1 et L2
- **Phase 4 :** Implémentation complète L1-L4

---

**Pour plus de détails :** Consultez `phase4/docs/04-EvaluationStrategie.md` pour la stratégie complète.

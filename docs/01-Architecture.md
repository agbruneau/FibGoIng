# Architecture et Décisions Techniques

> **Version :** 2.0.0 | **Statut :** Simplifié | **Dernière révision :** Janvier 2026

Ce document présente les **3 décisions architecturales clés** du projet AgentMeshKafka. Pour plus de détails, consultez la documentation complète dans `phase4/docs/`.

---

## ADR-001 : Architecture Événementielle via Kafka

**Contexte :** Les agents autonomes IA nécessitent une communication asynchrone pour éviter le blocage dû à la latence des LLM.

**Décision :** Utilisation d'**Apache Kafka** comme backbone de communication. Les agents publient et consomment des événements via des topics.

**Conséquences :**
- ✅ Découplage temporel et spatial
- ✅ Scalabilité horizontale
- ✅ Observabilité via le journal Kafka
- ⚠️ Complexité d'infrastructure

**Référence :** Phase 1+ pour l'implémentation.

---

## ADR-002 : Gouvernance des Données via Avro

**Contexte :** Les agents LLM peuvent produire des formats variables, risquant de briser les agents en aval.

**Décision :** Utilisation d'**Apache Avro** et **Schema Registry** pour valider les messages avant publication. Politique de compatibilité : `FORWARD`.

**Conséquences :**
- ✅ Contrats explicites et typés
- ✅ Prévention d'erreurs de format
- ⚠️ Overhead de validation

**Référence :** Phase 4 pour l'implémentation complète.

---

## ADR-003 : Pattern ReAct pour les Agents

**Contexte :** Les agents doivent agir, pas seulement parler. Un simple appel LLM est insuffisant.

**Décision :** Implémentation du pattern **ReAct (Reason + Act)** :
1. **Thought** : Analyse de la situation
2. **Action** : Sélection d'un outil
3. **Observation** : Résultat de l'outil
4. **Final Answer** : Synthèse

**Conséquences :**
- ✅ Capacité d'interaction avec le monde réel
- ✅ Explicabilité via Chain of Thought
- ⚠️ Coût et latence accrus

**Référence :** Toutes les phases utilisent ce pattern.

---

## Architecture du Système

Le système repose sur trois piliers :

1. **Système Nerveux** : Kafka (communication)
2. **Cerveau** : Agents LLM avec ReAct
3. **Système Immunitaire** : Validation et sécurité

---

**Pour plus de détails :** Consultez `phase4/docs/01-ArchitectureDecisions.md` pour les ADRs complets.

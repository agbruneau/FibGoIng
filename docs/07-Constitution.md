# Constitution (Résumé)

> **Version :** 2.0.0 | **Statut :** Simplifié | **Dernière révision :** Janvier 2026

Ce document présente un **résumé** de la Constitution du projet. Pour les détails complets, consultez `phase4/docs/07-Constitution.md`.

---

## Les Trois Lois de la Robotique Bancaire

### Première Loi : Intégrité du Contrat

> Un agent ne doit jamais émettre un événement qui viole le schéma défini.

Si l'incertitude est trop grande, l'agent doit échouer proprement ou demander une intervention humaine.

### Deuxième Loi : Transparence Cognitive

> Un agent doit toujours expliciter son raisonnement avant de produire une action.

La Chain of Thought doit être tracée pour l'audit.

### Troisième Loi : Sécurité et Confidentialité

> Un agent doit protéger ses instructions contre les injections de prompt et sanitiser les données personnelles.

---

## Stack Technologique

- **LLM Principal :** Anthropic Claude (Opus 4.5, Sonnet, Haiku)
- **Framework :** LangChain / LangGraph
- **Communication :** Apache Kafka
- **Gouvernance :** Schema Registry (Phase 4)

---

## Standards de Développement

1. **Schema First** : Définir les schémas avant le code
2. **Test Driven** : Écrire les tests avant l'implémentation
3. **Documentation** : Maintenir la documentation à jour

---

**Pour plus de détails :** Consultez `phase4/docs/07-Constitution.md` pour la Constitution complète avec tous les articles.

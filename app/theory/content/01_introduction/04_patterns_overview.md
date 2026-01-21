# Vue d'Ensemble des Patterns

Les **patterns d'intégration** sont des solutions éprouvées à des problèmes récurrents. Ce parcours couvre les patterns les plus importants, organisés par pilier.

## 🔗 Patterns d'Intégration Applicative

| Pattern | Problème résolu | Quand l'utiliser |
|---------|-----------------|-----------------|
| **API Gateway** | Point d'entrée unique | Exposition d'APIs à des partenaires |
| **Backend for Frontend** | Adaptation par canal | Mobile vs Web vs Partenaires |
| **API Composition** | Agrégation de données | Vue 360° client |
| **Anti-Corruption Layer** | Isolation du domaine | Intégration de systèmes legacy |
| **Strangler Fig** | Migration progressive | Modernisation sans big bang |

## ⚡ Patterns d'Intégration Événementielle

| Pattern | Problème résolu | Quand l'utiliser |
|---------|-----------------|-----------------|
| **Message Queue** | Communication point-à-point | Traitement asynchrone |
| **Publish/Subscribe** | Diffusion multi-consommateurs | Notification d'événements |
| **Event Sourcing** | Historique des changements | Audit, replay, debugging |
| **CQRS** | Séparation lecture/écriture | Optimisation performances |
| **Saga** | Transactions distribuées | Workflows multi-services |
| **Outbox** | Atomicité DB + événement | Fiabilité publication |

## 📊 Patterns d'Intégration de Données

| Pattern | Problème résolu | Quand l'utiliser |
|---------|-----------------|-----------------|
| **ETL** | Chargement batch | Alimentation data warehouse |
| **CDC** | Capture incrémentale | Synchronisation temps réel |
| **Data Pipeline** | Orchestration de flux | Transformations complexes |
| **MDM** | Données de référence | Golden record client |
| **Data Virtualization** | Vue fédérée | Requêtes multi-sources |

## 🛡️ Patterns Transversaux

| Pattern | Problème résolu | Quand l'utiliser |
|---------|-----------------|-----------------|
| **Circuit Breaker** | Pannes en cascade | Appels services tiers |
| **Retry + Backoff** | Erreurs temporaires | Fiabilisation des appels |
| **Bulkhead** | Isolation des ressources | Limiter l'impact des pannes |
| **Distributed Tracing** | Visibilité end-to-end | Debugging distribué |

---

## Comment choisir ?

```
Quel est le besoin principal ?

├─▶ Appeler une fonction d'un autre système
│   └─▶ 🔗 INTÉGRATION APPLICATIONS
│       └─ Réponse immédiate ? → REST/gRPC
│       └─ Peut attendre ? → Message Queue

├─▶ Réagir à un événement métier
│   └─▶ ⚡ INTÉGRATION ÉVÉNEMENTS
│       └─ Plusieurs consommateurs ? → Pub/Sub
│       └─ Un seul consommateur ? → Queue
│       └─ Workflow long ? → Saga

└─▶ Synchroniser/Analyser des données
    └─▶ 📊 INTÉGRATION DONNÉES
        └─ Temps réel requis ? → CDC
        └─ Batch OK ? → ETL
        └─ Sans copie ? → Virtualization
```

---

## Prochaines étapes

Ce module vous a présenté les fondamentaux. Dans les modules suivants, vous allez :

1. **Module 2** : Découvrir le domaine métier de l'assurance
2. **Modules 3-5** : Approfondir l'intégration applicative
3. **Modules 6-8** : Maîtriser l'intégration événementielle
4. **Modules 9-11** : Explorer l'intégration de données
5. **Modules 12-14** : Apprendre les patterns transversaux
6. **Modules 15-16** : Synthétiser et pratiquer

Bonne exploration !

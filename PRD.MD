# PRD - Product Requirements Document
# EDA-Lab : Simulateur d'Architecture Événementielle

**Version :** 1.1
**Date :** 2026-01-20
**Statut :** Approuvé

---

## 1. Vue d'ensemble

### 1.1 Description du projet

**EDA-Lab** est une application académique de simulation d'interopérabilité dans un écosystème d'entreprise fondé sur l'architecture événementielle (EDA - Event Driven Architecture). L'application permet d'apprendre et d'expérimenter l'implémentation et l'exploitation des patrons d'architecture EDA à travers une simulation automatisée de domaines métier interconnectés.

### 1.2 Contexte

| Élément | Description |
|---------|-------------|
| **Type** | Outil d'apprentissage personnel |
| **Utilisateur cible** | Architecte de domaine spécialisé en interopérabilité des systèmes |
| **Approche** | Itérative et incrémentale |

### 1.3 Objectifs d'apprentissage

| Priorité | Objectif |
|----------|----------|
| **1** | Maîtriser l'implémentation technique des patrons EDA avec Apache Kafka |
| **2** | Comprendre les compromis architecturaux (couplage, latence, résilience) |
| **3** | Visualiser les flux d'événements en temps réel dans une simulation entièrement automatisée |

### 1.4 Critères de succès

| Critère | Mesure |
|---------|--------|
| **Infrastructure opérationnelle** | `make test-infra` passe sans erreur |
| **Flux Pub/Sub fonctionnel** | Événements produits, consommés et persistés en base |
| **Visualisation temps réel** | WebSocket diffuse les événements vers React Flow |
| **Tests E2E** | `make test-e2e` passe pour chaque scénario prédéfini |
| **Observabilité** | Dashboard Grafana affiche les métriques Kafka |

---

## 2. Domaine métier

### 2.1 Domaines simulés

L'application simule un **écosystème de groupe financier intégré** composé de trois domaines :

| Domaine | Description |
|---------|-------------|
| **Bancaire** | Gestion des comptes, transactions, virements |
| **Assurance de Personne** | Contrats vie, santé, prévoyance |
| **Assurance Dommage** | Contrats auto, habitation, sinistres |

### 2.2 Flux d'interopérabilité

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  BANCAIRE   │◄────┤    CLIENT 360°      ├────►│ ASSURANCE PERS.  │
│             │     │  (Vue unifiée)      │     │                  │
└──────┬──────┘     └─────────────────────┘     └────────┬─────────┘
       │                                                  │
       │            ┌─────────────────────┐              │
       │            │ ASSURANCE DOMMAGE   │              │
       └───────────►│                     │◄─────────────┘
                    └─────────────────────┘
```

| Flux | Description |
|------|-------------|
| **Client 360°** | Vision unifiée du client partagée entre tous les domaines |
| **Paiement de primes** | Prélèvement des primes d'assurance via le compte bancaire |
| **Indemnisation sinistres** | Versement des indemnisations sur le compte bancaire |

---

## 3. Roadmap des patrons EDA

> **Note**: Ce projet utilise deux systèmes de numérotation:
> - **Itérations (1-8)**: Correspondent aux **patrons EDA** à implémenter (ce document)
> - **Phases techniques (0-8)**: Correspondent aux **étapes de construction** du MVP (voir PLAN.MD)
>
> L'**Itération 1 (MVP)** est construite via les **Phases techniques 0-8** du PLAN.MD.

### 3.1 MVP (Itération 1) - Pub/Sub

**Objectif**: Infrastructure fonctionnelle avec flux Pub/Sub complet sur le domaine bancaire

| Composant | Scope | Critère de validation |
|-----------|-------|----------------------|
| Infrastructure Docker | Kafka KRaft + Schema Registry + PostgreSQL | `make test-infra` passe |
| Schémas Avro | 4 événements bancaires | Schémas enregistrés dans Registry |
| Service Simulator | Génère des événements à débit configurable | API `/simulation/start` fonctionne |
| Service Bancaire | Consomme et persiste les événements | Données visibles en base |
| Service Gateway | Proxy REST + WebSocket temps réel | WebSocket diffuse les événements |
| Observabilité | Prometheus + Grafana | Dashboard affiche messages/sec |
| Web UI | Start/Stop + visualisation React Flow | Interface utilisable |

**Hors scope MVP**: Jaeger, Loki, Domaines Assurance, Event Sourcing, CQRS, Sagas

### 3.2 Itérations suivantes

| Itération | Patron | Description | Domaines ajoutés |
|-----------|--------|-------------|------------------|
| **2** | **Event Sourcing** | Stockage de l'état comme séquence d'événements | Assurance Personne, Assurance Dommage |
| **3** | **CQRS** | Séparation des modèles de lecture et d'écriture | Client 360 |
| **4** | **Saga Choreography** | Transactions distribuées par événements décentralisés | - |
| **5** | **Saga Orchestration** | Transactions distribuées par coordinateur central | - |
| **6** | **Event Streaming** | Traitement continu de flux avec Kafka Streams | - |
| **7** | **Dead Letter Queue** | Gestion des événements en erreur | - |
| **8** | **Outbox Pattern** | Garantie de livraison transactionnelle | - |

---

## 4. Catalogue des événements

### 4.1 Domaine Bancaire

| Événement | Description | Topic Kafka |
|-----------|-------------|-------------|
| `CompteOuvert` | Ouverture d'un nouveau compte bancaire | `bancaire.compte.ouvert` |
| `CompteFerme` | Fermeture d'un compte bancaire | `bancaire.compte.ferme` |
| `DepotEffectue` | Dépôt d'argent sur un compte | `bancaire.depot.effectue` |
| `RetraitEffectue` | Retrait d'argent d'un compte | `bancaire.retrait.effectue` |
| `VirementEmis` | Émission d'un virement sortant | `bancaire.virement.emis` |
| `VirementRecu` | Réception d'un virement entrant | `bancaire.virement.recu` |
| `PaiementPrimeEffectue` | Paiement d'une prime d'assurance | `bancaire.paiement-prime.effectue` |

### 4.2 Domaine Assurance de Personne

| Événement | Description | Topic Kafka |
|-----------|-------------|-------------|
| `ContratSouscrit` | Souscription d'un contrat vie/santé/prévoyance | `assurance-personne.contrat.souscrit` |
| `ContratResilie` | Résiliation d'un contrat | `assurance-personne.contrat.resilie` |
| `BeneficiaireModifie` | Modification du bénéficiaire d'un contrat | `assurance-personne.beneficiaire.modifie` |
| `PrimeAppelee` | Appel de prime émis | `assurance-personne.prime.appelee` |
| `PrimeEncaissee` | Prime encaissée avec succès | `assurance-personne.prime.encaissee` |
| `SinistreVieDepose` | Déclaration d'un sinistre vie | `assurance-personne.sinistre.depose` |
| `IndemnisationVieEmise` | Émission d'une indemnisation vie | `assurance-personne.indemnisation.emise` |

### 4.3 Domaine Assurance Dommage

| Événement | Description | Topic Kafka |
|-----------|-------------|-------------|
| `ContratAutoSouscrit` | Souscription d'un contrat auto | `assurance-dommage.contrat-auto.souscrit` |
| `ContratHabitationSouscrit` | Souscription d'un contrat habitation | `assurance-dommage.contrat-habitation.souscrit` |
| `ContratResilie` | Résiliation d'un contrat dommage | `assurance-dommage.contrat.resilie` |
| `SinistreAutoDepose` | Déclaration d'un sinistre auto | `assurance-dommage.sinistre-auto.depose` |
| `SinistreHabitationDepose` | Déclaration d'un sinistre habitation | `assurance-dommage.sinistre-habitation.depose` |
| `ExpertisePlanifiee` | Planification d'une expertise | `assurance-dommage.expertise.planifiee` |
| `IndemnisationDommageEmise` | Émission d'une indemnisation dommage | `assurance-dommage.indemnisation.emise` |

### 4.4 Domaine Client 360

| Événement | Description | Topic Kafka |
|-----------|-------------|-------------|
| `ProfilClientCree` | Création d'un profil client unifié | `client.profil.cree` |
| `ProfilClientMisAJour` | Mise à jour du profil client | `client.profil.mis-a-jour` |
| `VueUnifieeGeneree` | Génération de la vue 360° du client | `client.vue-unifiee.generee` |

### 4.5 Topics système

| Topic | Usage |
|-------|-------|
| `system.dlq` | Dead Letter Queue pour événements en erreur |
| `system.saga.events` | Coordination des transactions distribuées |

---

## 5. Architecture technique

### 5.1 Stack technologique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Message Broker** | Confluent Platform Community (KRaft) | Standard entreprise, Schema Registry intégré |
| **Sérialisation** | Apache Avro + Schema Registry | Gouvernance des schémas, évolution contrôlée |
| **Langage backend** | Go | Performance, légèreté des conteneurs |
| **Persistance** | PostgreSQL | Polyvalent, ACID, adapté pour Event Sourcing et Outbox |
| **Frontend** | React + React Flow | Écosystème mature, visualisation de flux interactive |
| **Conteneurisation** | Docker Compose | Simplicité, environnement local tout-en-un |

### 5.2 Convention de nommage

**Topics Kafka** : `<domaine>.<entite>.<action>`
- Les mots composés dans l'entité utilisent le tiret (`paiement-prime`)
- L'action est toujours en minuscules (`ouvert`, `effectue`, `emis`)
- Le domaine correspond au service émetteur

**Avro Namespace** : `com.edalab.<domaine>.events`

| Domaine | Namespace Avro |
|---------|----------------|
| Bancaire | `com.edalab.bancaire.events` |
| Assurance Personne | `com.edalab.assurance.personne.events` |
| Assurance Dommage | `com.edalab.assurance.dommage.events` |
| Client 360 | `com.edalab.client.events` |
| Système | `com.edalab.system.events` |

### 5.3 Architecture des services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              EDA-LAB                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  SERVICES MÉTIER                                                        │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │  bancaire   │  │ assurance-pers.  │  │ assurance-domm.  │           │
│  └─────────────┘  └──────────────────┘  └──────────────────┘           │
├─────────────────────────────────────────────────────────────────────────┤
│  SERVICES TRANSVERSES                                                   │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ client-360  │  │   orchestrator   │  │    simulator     │           │
│  └─────────────┘  └──────────────────┘  └──────────────────┘           │
│                   ┌──────────────────┐                                  │
│                   │     gateway      │  (API REST + WebSocket)          │
│                   └──────────────────┘                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                                         │
│  ┌───────────┐ ┌─────────────┐ ┌────────────┐ ┌─────────────────┐      │
│  │   Kafka   │ │  Schema Reg │ │ PostgreSQL │ │ Prometheus/Graf │      │
│  │  (KRaft)  │ │  (Confluent)│ │            │ │ Jaeger/Loki     │      │
│  └───────────┘ └─────────────┘ └────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Description des services

| Service | Responsabilité |
|---------|----------------|
| `bancaire` | Gestion des comptes, transactions, virements |
| `assurance-personne` | Gestion des contrats et sinistres vie/santé/prévoyance |
| `assurance-dommage` | Gestion des contrats et sinistres auto/habitation |
| `client-360` | Agrégation de la vue client unifiée |
| `orchestrator` | Coordination des sagas et transactions distribuées |
| `simulator` | Génération automatique d'événements fictifs |
| `gateway` | API REST pour le contrôle + WebSocket pour temps réel |

### 5.5 Stack d'observabilité

| Fonction | Outil |
|----------|-------|
| **Métriques** | Prometheus + Grafana |
| **Traçage distribué** | Jaeger (OpenTelemetry) |
| **Logs centralisés** | Loki + Grafana |

---

## 6. Interface utilisateur

### 6.1 Web UI - Contrôle de simulation

| Fonctionnalité | Description |
|----------------|-------------|
| **Start/Stop** | Boutons pour démarrer et arrêter la simulation |
| **Sélection de scénario** | Choix parmi les scénarios YAML prédéfinis |
| **Paramètres dynamiques** | Ajustement du débit, durée, etc. à la volée |
| **Déclenchement chaos** | Boutons pour activer les scénarios de défaillance |

### 6.2 Dashboard de visualisation (React Flow)

| Fonctionnalité | Description |
|----------------|-------------|
| **Graphe des services** | Visualisation des nodes (services) et edges (flux) |
| **Animation temps réel** | Événements circulant entre services avec animation |
| **Compteurs live** | Nombre d'événements par topic |
| **État des services** | Indicateurs de santé (vert/orange/rouge) |

### 6.3 Grafana Dashboards

| Dashboard | Métriques |
|-----------|-----------|
| **Kafka Overview** | Messages/sec, lag consommateurs, partitions |
| **Services Health** | CPU, mémoire, latence par service |
| **Business Metrics** | Événements par domaine, flux d'interopérabilité |

---

## 7. Configuration des scénarios

### 7.1 Structure d'un scénario (YAML)

```yaml
scenario:
  name: "flux-paiement-prime"
  description: "Simulation du flux de paiement de prime d'assurance"
  duration: 300s

  producers:
    - domain: bancaire
      event: compte-ouvert
      rate: 10/s
      data_generator: fake-client

    - domain: assurance-personne
      event: contrat-souscrit
      rate: 5/s
      depends_on: bancaire.compte.ouvert

    - domain: assurance-personne
      event: prime-appelee
      rate: 5/s
      delay: 10s

  consumers:
    - service: bancaire
      topics:
        - assurance-personne.prime.appelee
      action: paiement-prime

  assertions:
    - topic: bancaire.paiement-prime.effectue
      min_count: 100
      max_latency: 500ms

  chaos:
    - type: consumer-lag
      target: service-bancaire
      trigger_at: 60s
      duration: 30s
```

### 7.2 Scénarios prédéfinis

| Scénario | Description | Flux exercé |
|----------|-------------|-------------|
| `flux-client-360` | Création de clients multi-domaines | Vision 360° |
| `flux-paiement-prime` | Appel et paiement de primes | Paiement primes |
| `flux-sinistre-auto` | Déclaration et indemnisation sinistre | Indemnisation |
| `flux-complet` | Cycle de vie complet client | Tous les flux |
| `stress-test` | Charge élevée pour tester les limites | Performance |

---

## 8. Chaos Engineering

### 8.1 Scénarios de défaillance

| Type | Description | Apprentissage visé |
|------|-------------|-------------------|
| **Consumer Lag** | Ralentir un consommateur pour accumuler du retard | Observer le backpressure, métriques de lag |
| **Service Down** | Arrêter un service temporairement | Tester la résilience, retry, Dead Letter Queue |
| **Network Latency** | Injecter de la latence réseau entre services | Impact sur les timeouts, comportement des sagas |
| **Duplicate Events** | Produire des événements en double | Valider l'idempotence des consommateurs |
| **Schema Evolution** | Modifier un schéma Avro en cours de simulation | Tester la compatibilité avant/arrière |

### 8.2 Déclenchement

- **Via Interface Web** : Boutons dédiés pour chaque type de chaos
- **Via YAML** : Configuration dans les scénarios avec `trigger_at` et `duration`
- **Via API REST** : Endpoints pour automatisation

---

## 9. Gestion des erreurs

### 9.1 Dead Letter Queue (DLQ)

**Structure message DLQ** :
```json
{
  "original_topic": "bancaire.compte.ouvert",
  "original_message": { },
  "error": {
    "type": "DESERIALIZATION_ERROR",
    "message": "Invalid Avro schema",
    "timestamp": "2026-01-20T00:00:00Z",
    "attempt_count": 3
  },
  "metadata": {
    "service": "bancaire",
    "consumer_group": "bancaire-group"
  }
}
```

### 9.2 Idempotence

| Événement | Clé d'idempotence | Stratégie |
|-----------|-------------------|-----------|
| CompteOuvert | `compte_id` | INSERT ... ON CONFLICT DO NOTHING |
| DepotEffectue | `event_id` | Table de tracking des événements traités |
| VirementEmis | `event_id` | Table de tracking des événements traités |

---

## 10. Références

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Platform](https://docs.confluent.io/)
- [Apache Avro Specification](https://avro.apache.org/docs/current/spec.html)
- [React Flow](https://reactflow.dev/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry](https://opentelemetry.io/)
- [testcontainers-go](https://golang.testcontainers.org/)

---

**Document généré le 2026-01-20**

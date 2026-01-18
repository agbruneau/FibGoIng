# Cahier des Charges - Simulation EDA Kafka
## Application Académique pour l'Interopérabilité en Écosystèmes d'Entreprise

---

## 1. Vue d'ensemble du projet

### 1.1 Objectif
Développer une simulation dans le domaine de l'interopérabilité en écosystèmes d'entreprise fondée sur Apache Kafka et les patrons d'architecture Event-Driven Architecture (EDA). Cette application académique vise l'apprentissage et l'expérimentation de l'implémentation et de l'exploitation de ces patrons d'architecture.

### 1.2 Public cible
- **Utilisateurs principaux** : Architectes de domaine en interopérabilité des systèmes dans une grande entreprise
- **Contexte d'utilisation** : 
  - Formation interne
  - Expérimentation/validation de concepts auprès des parties prenantes

### 1.3 Domaine métier
Domaine financier couvrant :
- Finance
- Bancaire
- Assurance de Personnes
- Assurance Dommages

### 1.4 Systèmes métier à simuler
1. **Traitement de transaction**
2. **Réclamation/Sinistre**
3. **Quotation/Émission de contrats d'assurance**

---

## 2. Architecture et Patrons d'Architecture

### 2.1 Infrastructure de base
- **Moteur d'événements** : Apache Kafka
- **Gestion des schémas** : Confluent Schema Registry
- **Format de sérialisation** : Avro
- **Event Store** : Kafka lui-même (topics avec rétention permanente)

### 2.2 Patrons d'architecture à implémenter (ordre d'implémentation)
Approche **incrémentale** : chaque patron est une version/étape séparée pour faciliter la formation.

1. **Producteur/Consommateur** (patron initial)
2. **Event Sourcing**
3. **CQRS (Command Query Responsibility Segregation)**
4. **Saga Pattern**
5. **Outbox Pattern**
6. **Event Streaming avec transformations**
7. **Pattern API Gateway + Kafka**

### 2.3 Mécanismes de résilience
- Mécanismes de retry automatique
- Dead Letter Queues (DLQ)
- Gestion des erreurs

### 2.4 Compatibilité des schémas
- Illustration de l'évolution des schémas Avro
- Support de la compatibilité forward/backward

---

## 3. Stack technique

### 3.1 Backend
- **Langage de programmation** : Go
- **Gestion des dépendances** : Go modules standard
- **Bibliothèques Kafka** : 
  - `confluent-kafka-go` (compatibilité avec Confluent Schema Registry)
  - `sarama` si nécessaire

### 3.2 Frontend
- **Framework** : React (choix pour facilité d'utilisation)
- **Visualisations** :
  - Liste des événements en temps réel
  - Graphique du flux d'événements entre services
  - Métriques agrégées

### 3.3 Infrastructure de déploiement
- **Orchestration** : Docker Compose
- **Environnement** : Local uniquement
- **Principe** : Simple d'utilisation et d'exploitation

### 3.4 Bases de données
- **Event Store** : Kafka (topics avec rétention permanente)
- **CQRS et autres composants** : SQLite (choix pour simplicité d'utilisation en local)

### 3.5 Observabilité
- **Métriques** : Prometheus/Grafana
- **Dashboards métier personnalisés** : Pour les domaines Finance, Bancaire, Assurance de Personnes et Assurance Dommages
- **Logs** : Accessibles via CLI

### 3.6 Gestion de la configuration
- **Format** : Fichiers de configuration (YAML, JSON, ou TOML)

---

## 4. Fonctionnalités

### 4.1 Génération d'événements
- **Mode** : Génération automatique en continu
- **Fréquence** : Événements toutes les 2 secondes (fréquence fixe)
- **Type** : Scénarios complets de bout en bout (cycles de vie complets des processus métier)
- **Domaines couverts** : Cas d'utilisation classiques liés à Finance, Bancaire, Assurance de Personnes et Assurance Dommages

### 4.2 Interface utilisateur

#### 4.2.1 Interface web (visualisation)
- Liste des événements en temps réel (type, payload, timestamp)
- Graphique du flux d'événements entre services
- Métriques agrégées (nombre d'événements par type, par service)
- Dashboards métier personnalisés

#### 4.2.2 CLI (contrôle)
- Contrôle basique et facile d'utilisation :
  - Démarrer/arrêter les services
  - Consulter les logs

### 4.3 Documentation des événements
- **Génération automatique** : Documentation technique générée automatiquement depuis les schémas Avro dans le Schema Registry

---

## 5. Qualité et tests

### 5.1 Couverture de tests
- **Niveau** : Tests complets (unitaires, intégration, end-to-end)
- **Couverture cible** : 80% de couverture de code

---

## 6. Documentation

### 6.1 Niveau de documentation
Documentation **complète et exhaustive** incluant :
- Guides d'architecture expliquant chaque patron
- Tutoriels pas à pas pour chaque patron
- Diagrammes d'architecture
- Scénarios métier illustrés

### 6.2 Guide de démarrage
- **Format** : README complet avec instructions pas à pas

---

## 7. Structure du projet

### 7.1 Organisation
- **Type** : Monorepo (tous les services dans un seul dépôt)
- **Approche** : Incrémentale (chaque patron = version/étape séparée)

### 7.2 Structure recommandée
```
projet/
├── cmd/                    # Points d'entrée des services
│   ├── producer/
│   ├── consumer/
│   ├── transaction-service/
│   ├── claim-service/
│   ├── quotation-service/
│   └── cli/
├── internal/               # Code interne
│   ├── kafka/             # Clients Kafka, producers, consumers
│   ├── schemas/           # Schémas Avro
│   ├── events/            # Définitions d'événements
│   ├── services/          # Logique métier des services
│   └── utils/             # Utilitaires partagés
├── web/                   # Application React
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── public/
├── configs/               # Fichiers de configuration
├── docker/                # Dockerfiles et configurations Docker
├── docker-compose.yml     # Orchestration des services
├── docs/                  # Documentation
│   ├── architecture/
│   ├── tutorials/
│   └── schemas/
├── tests/                 # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── README.md              # Guide de démarrage complet
```

---

## 8. Composants Docker Compose

### 8.1 Services infrastructure
- Apache Kafka (cluster)
- Zookeeper (si nécessaire selon version Kafka)
- Confluent Schema Registry
- Prometheus
- Grafana

### 8.2 Services applicatifs
- Services Go (producteurs/consommateurs)
- Application React (frontend)
- Bases de données (SQLite via volumes ou PostgreSQL si nécessaire)

---

## 9. Scénarios métier à implémenter

### 9.1 Domaine Transaction bancaire
Scénarios complets illustrant le cycle de vie d'une transaction :
- Initiation de transaction
- Validation
- Confirmation
- Comptabilisation

### 9.2 Domaine Réclamation/Sinistre
Scénarios complets illustrant le traitement d'une réclamation :
- Dépôt de réclamation
- Enquête
- Évaluation
- Règlement
- Clôture

### 9.3 Domaine Quotation/Émission de contrats
Scénarios complets illustrant l'émission d'un contrat :
- Demande de quotation
- Calcul des primes
- Validation des conditions
- Émission du contrat
- Activation du contrat

---

## 10. Métriques et observabilité

### 10.1 Métriques techniques
- Throughput Kafka (messages/seconde)
- Latence de traitement
- Taux d'erreur
- Utilisation des partitions
- Lag des consommateurs

### 10.2 Métriques métier (dashboards personnalisés)
- Nombre de transactions traitées
- Nombre de réclamations en cours
- Nombre de contrats émis
- Temps moyen de traitement par type d'événement

---

## 11. Critères de succès

### 11.1 Fonctionnel
- ✅ Tous les patrons d'architecture implémentés dans l'ordre défini
- ✅ Génération automatique d'événements fonctionnelle
- ✅ Interface web et CLI opérationnelles
- ✅ Observabilité complète (Prometheus/Grafana + dashboards métier)

### 11.2 Qualité
- ✅ 80% de couverture de tests
- ✅ Documentation complète et exhaustive
- ✅ Code maintenable et bien structuré

### 11.3 Facilité d'utilisation
- ✅ Démarrage simple avec Docker Compose
- ✅ README complet permettant un démarrage rapide
- ✅ Interface intuitive pour les architectes

---

## 12. Contraintes et considérations

### 12.1 Environnement
- Développement et exécution **local uniquement**
- Privilégier la **simplicité d'utilisation et d'exploitation**
- Pas de déploiement cloud nécessaire

### 12.2 Génération de code
- **Méthode** : Application entièrement générée à l'aide de Claude Code et Cursor
- **Principe** : Automatisation maximale de la génération du code

---

## 13. Livrables

### 13.1 Code source
- Code source complet du projet (monorepo)
- Configuration Docker Compose
- Fichiers de configuration
- Schémas Avro

### 13.2 Documentation
- README complet avec guide de démarrage
- Documentation d'architecture (par patron)
- Tutoriels pas à pas
- Diagrammes d'architecture
- Documentation des événements (générée automatiquement)

### 13.3 Tests
- Suite de tests complète (80% de couverture)
- Scripts d'exécution des tests

---

## 14. Phases de développement (approche incrémentale)

### Phase 1 : Producteur/Consommateur
- Infrastructure Kafka de base
- Premier service producteur
- Premier service consommateur
- Interface web basique
- CLI basique

### Phase 2 : Event Sourcing
- Implémentation de l'Event Store avec Kafka
- Projection d'événements
- Reconstruction d'état

### Phase 3 : CQRS
- Séparation commande/requête
- Read models avec SQLite
- Synchronisation read models

### Phase 4 : Saga Pattern
- Orchestration de sagas
- Compensation en cas d'échec

### Phase 5 : Outbox Pattern
- Transaction outbox
- Relais des événements

### Phase 6 : Event Streaming avec transformations
- Transformations d'événements
- Enrichissement de données

### Phase 7 : API Gateway + Kafka
- Gateway API
- Exposition REST des événements

---

## 15. Notes pour le développeur

### 15.1 Technologies à privilégier
- Go pour la simplicité et les performances
- React pour la facilité d'utilisation en frontend
- SQLite pour la simplicité en local
- Docker Compose pour faciliter le démarrage

### 15.2 Points d'attention
- Maintenir la simplicité d'utilisation (public cible : architectes)
- Documentation exhaustive pour faciliter l'apprentissage
- Tests complets pour garantir la qualité
- Approche incrémentale pour permettre l'apprentissage progressif

### 15.3 Génération automatique
- Privilégier la génération automatique de code avec Claude Code et Cursor
- Documenter les événements automatiquement depuis les schémas Avro
- Automatiser la configuration Docker Compose

---

**Date de création** : [Date]
**Version** : 1.0
**Statut** : À développer

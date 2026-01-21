# Les Trois Piliers de l'Intégration

L'intégration d'entreprise repose sur **trois approches complémentaires**, chacune adaptée à des besoins spécifiques.

## 🔗 Pilier 1 : Intégration des Applications

L'intégration applicative permet aux systèmes de **communiquer directement** via des interfaces bien définies.

### Caractéristiques

- **Communication synchrone** (requête/réponse)
- **Couplage moyen à fort**
- **Latence temps réel**
- **Volume transactionnel**

### Patterns typiques

- API REST / GraphQL / gRPC
- API Gateway
- Backend for Frontend (BFF)
- Service Mesh

### Cas d'usage

> Un portail web appelle l'API du moteur de devis pour calculer une prime d'assurance en temps réel.

---

## ⚡ Pilier 2 : Intégration des Événements

L'intégration événementielle permet un **découplage fort** entre producteurs et consommateurs via des messages asynchrones.

### Caractéristiques

- **Communication asynchrone**
- **Couplage faible**
- **Latence near real-time**
- **Réactivité aux changements**

### Patterns typiques

- Message Queue (point-à-point)
- Publish/Subscribe (topics)
- Event Sourcing
- Saga (transactions distribuées)
- CQRS

### Cas d'usage

> Quand une police est créée, un événement `PolicyCreated` est publié. Le service de facturation et le service de notification le reçoivent indépendamment.

---

## 📊 Pilier 3 : Intégration des Données

L'intégration de données assure la **cohérence** et la **disponibilité** des données à travers l'écosystème.

### Caractéristiques

- **Volumes massifs**
- **Batch et temps réel**
- **Focus sur la qualité**
- **Traçabilité (lineage)**

### Patterns typiques

- ETL (Extract-Transform-Load)
- CDC (Change Data Capture)
- Data Pipeline
- Master Data Management (MDM)
- Data Virtualization

### Cas d'usage

> Chaque nuit, un pipeline ETL extrait les sinistres du jour et les charge dans le data warehouse pour le reporting.

---

## Comparatif des trois approches

| Critère | 🔗 Applications | ⚡ Événements | 📊 Données |
|---------|----------------|--------------|-----------|
| **Couplage** | Moyen-Fort | Faible | Variable |
| **Latence** | Temps réel | Near real-time | Batch à temps réel |
| **Volume** | Transactionnel | Transactionnel | Massif |
| **Cas d'usage** | Requête/Réponse | Réaction, Workflow | Analytics, Sync |

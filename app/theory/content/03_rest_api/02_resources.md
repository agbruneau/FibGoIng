# Design de Ressources REST

## Résumé

Le design de ressources est l'art de modéliser votre domaine métier en **ressources** accessibles via des URLs. C'est la fondation d'une API REST bien conçue.

## Principes Fondamentaux

### Noms vs Verbes

Les URLs doivent représenter des **noms** (ressources), pas des **verbes** (actions).

```
❌ Mauvais :
POST /createQuote
GET /getQuoteById?id=Q001
POST /acceptQuote

✅ Bon :
POST /quotes
GET /quotes/Q001
POST /quotes/Q001/accept
```

### Pluriel vs Singulier

Utilisez le **pluriel** pour les collections :

```
GET /quotes          → Collection de devis
GET /quotes/Q001     → Un devis spécifique
GET /policies        → Collection de polices
GET /policies/POL-001 → Une police spécifique
```

### Hiérarchie et Relations

Les URLs reflètent les relations parent-enfant :

```
# Sinistres d'une police
GET /policies/POL-001/claims

# Documents d'un sinistre
GET /claims/CLM-001/documents

# Factures d'une police
GET /policies/POL-001/invoices
```

### Actions Non-CRUD

Pour les opérations qui ne sont pas du simple CRUD, utilisez des **sous-ressources** ou des **actions** :

```
# Activation d'une police
POST /policies/POL-001/activate

# Validation d'un devis
POST /quotes/Q001/validate

# Règlement d'un sinistre
POST /claims/CLM-001/settle
```

## Modélisation Domaine Assurance

### Ressources Principales

| Ressource | Description | Exemple URL |
|-----------|-------------|-------------|
| `/quotes` | Devis | /quotes/Q001 |
| `/policies` | Polices | /policies/POL-2024-001 |
| `/claims` | Sinistres | /claims/CLM-2024-001 |
| `/customers` | Clients | /customers/C001 |
| `/invoices` | Factures | /invoices/INV-2024-001 |

### Relations Entre Ressources

```
Customer (1) ──────────── (N) Quote
     │                         │
     │                         │ convertTo
     │                         ▼
     └─────────────────── (N) Policy
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                    ▼          ▼          ▼
                  Claim     Invoice    Document
```

### Exemple d'API Complète

```
# Clients
GET    /customers                    Liste des clients
POST   /customers                    Créer un client
GET    /customers/{id}               Détail client
PUT    /customers/{id}               Modifier client
DELETE /customers/{id}               Supprimer client

# Devis
GET    /quotes                       Liste des devis
POST   /quotes                       Créer un devis
GET    /quotes/{id}                  Détail devis
POST   /quotes/{id}/accept           Accepter devis
POST   /quotes/{id}/reject           Rejeter devis

# Polices
GET    /policies                     Liste des polices
POST   /policies                     Créer police (depuis devis)
GET    /policies/{number}            Détail police
POST   /policies/{number}/activate   Activer police
POST   /policies/{number}/suspend    Suspendre police
POST   /policies/{number}/renew      Renouveler police
DELETE /policies/{number}            Résilier police

# Polices - Sous-ressources
GET    /policies/{number}/claims     Sinistres de la police
GET    /policies/{number}/invoices   Factures de la police
GET    /policies/{number}/documents  Documents de la police
```

## Filtrage, Tri et Pagination

### Query Parameters

```
# Filtrage
GET /policies?status=ACTIVE&product=AUTO

# Tri
GET /claims?sort=incident_date&order=desc

# Pagination
GET /invoices?page=2&limit=20

# Recherche
GET /customers?search=Dupont
```

### Réponse Paginée

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 156,
    "pages": 8
  },
  "_links": {
    "self": "/invoices?page=2&limit=20",
    "first": "/invoices?page=1&limit=20",
    "prev": "/invoices?page=1&limit=20",
    "next": "/invoices?page=3&limit=20",
    "last": "/invoices?page=8&limit=20"
  }
}
```

## Anti-Patterns à Éviter

| Anti-Pattern | Exemple | Solution |
|--------------|---------|----------|
| Verbes dans l'URL | /getPolicy | GET /policies/{id} |
| Trop de niveaux | /a/b/c/d/e/f | Max 3 niveaux |
| Incohérence | /quote vs /policies | Toujours pluriel |
| IDs séquentiels | /policies/1 | UUIDs ou codes métier |

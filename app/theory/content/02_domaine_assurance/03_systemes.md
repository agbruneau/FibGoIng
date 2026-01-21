# Systèmes de l'Écosystème

## Architecture d'un assureur typique

Un assureur moderne dispose de plusieurs systèmes spécialisés qui doivent communiquer entre eux.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ÉCOSYSTÈME ASSURANCE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   FRONT-END                    BACK-END                   EXTERNE   │
│   ─────────                    ────────                   ────────  │
│                                                                      │
│   ┌─────────┐                 ┌─────────────┐           ┌─────────┐│
│   │ Portail │                 │ Quote Engine│           │External ││
│   │   Web   │────────────────▶│             │◀──────────│ Rating  ││
│   └─────────┘                 └─────────────┘           └─────────┘│
│                                      │                              │
│   ┌─────────┐                        ▼                              │
│   │   App   │                 ┌─────────────┐                       │
│   │ Mobile  │────────────────▶│ Policy Admin│                       │
│   └─────────┘                 │   System    │                       │
│                               └──────┬──────┘                       │
│   ┌─────────┐                        │                              │
│   │Courtiers│                 ┌──────┼──────┬──────────┐           │
│   │   B2B   │                 ▼      ▼      ▼          ▼           │
│   └─────────┘          ┌───────┐┌───────┐┌───────┐┌─────────┐     │
│                        │Claims ││Billing││ Notif ││ DocMgmt │     │
│                        └───────┘└───────┘└───────┘└─────────┘     │
│                                                                      │
│                               ┌─────────────┐                       │
│                               │ Customer Hub│                       │
│                               │ (Référentiel)│                      │
│                               └─────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Description des systèmes

### 1. Quote Engine (Moteur de Devis)

**Rôle** : Calculer les primes d'assurance en fonction des risques.

| Aspect | Détail |
|--------|--------|
| **Type** | Service de calcul |
| **Criticité** | Haute |
| **Latence attendue** | < 500ms |
| **APIs** | POST /quotes, GET /quotes/{id} |

### 2. Policy Admin System (PAS)

**Rôle** : Gérer le cycle de vie complet des polices d'assurance.

| Aspect | Détail |
|--------|--------|
| **Type** | Core system |
| **Criticité** | Critique |
| **Latence attendue** | < 1s |
| **APIs** | CRUD /policies |

### 3. Claims Management

**Rôle** : Gérer les déclarations et le traitement des sinistres.

| Aspect | Détail |
|--------|--------|
| **Type** | Système métier |
| **Criticité** | Haute |
| **Latence attendue** | < 2s |
| **APIs** | POST /claims, PUT /claims/{id}/status |

### 4. Billing System

**Rôle** : Gérer la facturation et les encaissements.

| Aspect | Détail |
|--------|--------|
| **Type** | Système financier |
| **Criticité** | Haute |
| **Latence attendue** | < 1s |
| **APIs** | POST /invoices, GET /invoices/policy/{id} |

### 5. Customer Hub

**Rôle** : Référentiel centralisé des données clients.

| Aspect | Détail |
|--------|--------|
| **Type** | Master Data |
| **Criticité** | Haute |
| **Latence attendue** | < 200ms |
| **APIs** | CRUD /customers |

### 6. Document Management

**Rôle** : Stocker et gérer les documents (contrats, justificatifs).

| Aspect | Détail |
|--------|--------|
| **Type** | GED |
| **Criticité** | Moyenne |
| **Latence attendue** | < 3s (upload) |
| **APIs** | POST /documents, GET /documents/{id} |

### 7. Notification Service

**Rôle** : Envoyer des notifications (email, SMS, push).

| Aspect | Détail |
|--------|--------|
| **Type** | Service technique |
| **Criticité** | Moyenne |
| **Latence attendue** | Asynchrone |
| **APIs** | POST /notifications |

### 8. External Rating API

**Rôle** : Obtenir des tarifs de référence externe.

| Aspect | Détail |
|--------|--------|
| **Type** | Service externe (tiers) |
| **Criticité** | Moyenne |
| **Latence attendue** | Variable (200ms-2s) |
| **APIs** | GET /rates |

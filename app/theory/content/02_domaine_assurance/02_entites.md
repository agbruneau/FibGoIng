# Entités Métier

## Les entités principales

Dans notre écosystème d'assurance simplifié, nous manipulons cinq entités principales.

### Customer (Client)

Le client est la personne physique ou morale qui souscrit une assurance.

```
Customer
├── id: string          # Identifiant unique (ex: "C001")
├── firstName: string   # Prénom
├── lastName: string    # Nom
├── email: string       # Email de contact
├── phone: string       # Téléphone
├── address: Address    # Adresse postale
└── createdAt: datetime # Date de création
```

### Quote (Devis)

Le devis est une proposition tarifaire avant souscription.

```
Quote
├── id: string          # Identifiant unique (ex: "Q-2024-001")
├── customerId: string  # Référence au client
├── product: string     # Type de produit ("AUTO" / "HABITATION")
├── riskData: object    # Données du risque
├── premium: decimal    # Prime estimée
├── validUntil: date    # Date de validité
├── status: string      # DRAFT / SENT / ACCEPTED / EXPIRED
└── createdAt: datetime # Date de création
```

### Policy (Police)

La police est le contrat d'assurance actif.

```
Policy
├── number: string      # Numéro de police (ex: "POL-2024-001")
├── customerId: string  # Référence au client
├── quoteId: string     # Devis d'origine (optionnel)
├── product: string     # Type de produit
├── coverages: array    # Liste des garanties
├── premium: decimal    # Prime annuelle
├── startDate: date     # Date de début
├── endDate: date       # Date de fin
├── status: string      # DRAFT / ACTIVE / SUSPENDED / CANCELLED
└── createdAt: datetime # Date d'émission
```

### Claim (Réclamation/Sinistre)

La réclamation représente une déclaration de sinistre.

```
Claim
├── number: string      # Numéro de sinistre (ex: "CLM-2024-001")
├── policyNumber: string# Police concernée
├── type: string        # ACCIDENT / THEFT / DAMAGE / OTHER
├── occurredAt: datetime# Date du sinistre
├── reportedAt: datetime# Date de déclaration
├── description: string # Description du sinistre
├── estimatedAmount: decimal # Montant estimé
├── settledAmount: decimal   # Montant réglé
├── status: string      # OPEN / IN_PROGRESS / SETTLED / REJECTED
└── documents: array    # Pièces jointes
```

### Invoice (Facture)

La facture représente une demande de paiement.

```
Invoice
├── number: string      # Numéro de facture (ex: "INV-2024-001")
├── policyNumber: string# Police concernée
├── amount: decimal     # Montant à payer
├── dueDate: date       # Date d'échéance
├── paidAt: datetime    # Date de paiement (si payé)
├── status: string      # PENDING / PAID / OVERDUE / CANCELLED
└── createdAt: datetime # Date d'émission
```

---

## Relations entre entités

```
┌──────────────┐
│   Customer   │
└──────┬───────┘
       │ 1:N
       ▼
┌──────────────┐      ┌──────────────┐
│    Quote     │─────▶│    Policy    │
└──────────────┘ 0:1  └──────┬───────┘
                             │ 1:N
                ┌────────────┼────────────┐
                ▼            ▼            ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │  Claim   │ │ Invoice  │ │ Document │
         └──────────┘ └──────────┘ └──────────┘
```

### Cardinalités

| Relation | Type | Description |
|----------|------|-------------|
| Customer → Quote | 1:N | Un client peut avoir plusieurs devis |
| Customer → Policy | 1:N | Un client peut avoir plusieurs polices |
| Quote → Policy | 0:1 | Un devis peut devenir une police |
| Policy → Claim | 1:N | Une police peut avoir plusieurs sinistres |
| Policy → Invoice | 1:N | Une police génère plusieurs factures |

# Domaine Métier : Assurance Dommage

## Les Processus Métier

L'assurance dommage (IARD - Incendie, Accidents et Risques Divers) couvre principalement l'**automobile** et l'**habitation**. Voici les processus clés.

### Vue d'ensemble du cycle de vie

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  QUOTATION  │───▶│ SOUSCRIPTION │───▶│   POLICE    │
│  (Devis)    │    │ (Underwriting)│   │  (Policy)   │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                              │
                   ┌──────────────────────────┼──────────────────────────┐
                   │                          │                          │
                   ▼                          ▼                          ▼
            ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
            │ RÉCLAMATION │           │ FACTURATION │           │RENOUVELLEMENT│
            │   (Claim)   │           │  (Billing)  │           │  (Renewal)   │
            └─────────────┘           └─────────────┘           └─────────────┘
```

---

## 1. Quotation (Devis)

Le processus de devis permet au client d'obtenir une **estimation de prime** avant de souscrire.

### Étapes

1. **Collecte des informations** - Données sur le client et le risque
2. **Évaluation du risque** - Analyse des facteurs de risque
3. **Calcul de la prime** - Application des règles tarifaires
4. **Présentation du devis** - Proposition avec détails des garanties

### Données clés

| Donnée | Exemple |
|--------|---------|
| Type de produit | Auto, Habitation |
| Informations client | Âge, adresse, historique |
| Données du risque | Véhicule, surface habitation |
| Garanties demandées | RC, vol, bris de glace |

### Intégrations typiques

- **Quote Engine** → Calcul de la prime
- **External Rating API** → Tarification externe
- **Customer Hub** → Informations client

---

## 2. Souscription (Underwriting)

La souscription est le processus d'**acceptation ou refus** du risque et d'émission de la police.

### Étapes

1. **Validation du devis** - Vérification des informations
2. **Décision d'acceptation** - Règles automatiques ou manuelles
3. **Émission de la police** - Création du contrat
4. **Génération des documents** - Conditions, attestation

### Points d'intégration

- **Policy Admin System (PAS)** → Création de la police
- **Document Management** → Génération des documents
- **Notification Service** → Confirmation au client

---

## 3. Gestion de la Police

Pendant la vie du contrat, plusieurs événements peuvent survenir.

### Types de modifications

| Type | Description |
|------|-------------|
| **Avenant** | Modification des garanties ou données |
| **Suspension** | Arrêt temporaire des garanties |
| **Résiliation** | Fin anticipée du contrat |
| **Renouvellement** | Prolongation à l'échéance |

---

## 4. Réclamation (Claim)

Lorsqu'un sinistre survient, le client déclare une réclamation.

### Cycle de vie d'une réclamation

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ DÉCLARÉ  │───▶│ EN COURS │───▶│ ÉVALUÉ   │───▶│ RÉGLÉ    │
│          │    │ D'ÉTUDE  │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │                               │
      │                               ▼
      │                        ┌──────────┐
      └───────────────────────▶│ REFUSÉ   │
                               │          │
                               └──────────┘
```

### Étapes

1. **Déclaration** - Le client signale le sinistre
2. **Instruction** - Collecte des justificatifs
3. **Évaluation** - Estimation du montant
4. **Décision** - Acceptation ou refus
5. **Règlement** - Paiement de l'indemnité

---

## 5. Facturation (Billing)

La facturation gère la **collecte des primes** auprès des assurés.

### Modes de paiement

- Annuel (100% à l'émission)
- Semestriel (2 échéances)
- Trimestriel (4 échéances)
- Mensuel (12 échéances)

### Processus

1. **Émission des factures** à chaque échéance
2. **Suivi des encaissements**
3. **Relances** en cas d'impayé
4. **Suspension/Résiliation** si non-paiement persistant

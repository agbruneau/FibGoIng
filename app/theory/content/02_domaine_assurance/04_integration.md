# Points d'Intégration

## Cartographie des flux

Voici les principaux flux d'intégration entre les systèmes.

### Flux Synchrones (🔗 Applications)

| Source | Cible | Déclencheur | Données |
|--------|-------|-------------|---------|
| Portail | Quote Engine | Demande de devis | Données risque |
| Quote Engine | External Rating | Calcul prime | Paramètres tarification |
| Portail | PAS | Souscription | Devis accepté |
| Portail | Customer Hub | Création client | Données client |
| App Mobile | Customer Hub | Consultation profil | ID client |
| Claims | Policy Admin | Vérification garanties | Numéro police |

### Flux Asynchrones (⚡ Événements)

| Producteur | Événement | Consommateurs |
|------------|-----------|---------------|
| PAS | PolicyCreated | Billing, Notifications, Audit |
| PAS | PolicyModified | Billing, Notifications |
| PAS | PolicyCancelled | Billing, Notifications |
| Claims | ClaimOpened | Notifications, Audit |
| Claims | ClaimSettled | Billing, Notifications |
| Billing | PaymentReceived | PAS, Notifications |
| Billing | PaymentOverdue | Notifications |

### Flux Batch (📊 Données)

| Source | Cible | Fréquence | Volume |
|--------|-------|-----------|--------|
| PAS | Data Warehouse | Quotidien | ~10K polices/jour |
| Claims | Data Warehouse | Quotidien | ~1K claims/jour |
| Billing | Data Warehouse | Quotidien | ~50K transactions/jour |
| All systems | Reporting | Temps réel (CDC) | Continu |

---

## Exemple de flux complet : Souscription

```
Utilisateur              Systèmes                    Événements
    │                        │                           │
    │  1. Demande devis     │                           │
    │───────────────────────▶│ Quote Engine             │
    │                        │────▶ External Rating     │
    │                        │◀────                     │
    │◀───────────────────────│ (Devis calculé)         │
    │                        │                           │
    │  2. Accepte devis     │                           │
    │───────────────────────▶│ PAS                      │
    │                        │ (Crée police)            │
    │                        │                           │
    │                        │─────────────────────────▶│ PolicyCreated
    │                        │                           │      │
    │                        │                           │      ├──▶ Billing
    │                        │                           │      │    (Crée facture)
    │                        │                           │      │
    │                        │                           │      ├──▶ Notifications
    │                        │                           │      │    (Email confirmation)
    │                        │                           │      │
    │                        │                           │      └──▶ DocMgmt
    │                        │                           │           (Génère documents)
    │                        │                           │
    │  3. Reçoit docs       │                           │
    │◀───────────────────────│ (via Notifications)      │
    │                        │                           │
```

---

## Défis d'intégration identifiés

| Défi | Contexte | Solution |
|------|----------|----------|
| **Latence External Rating** | Le service externe est lent | Circuit Breaker + Cache |
| **Cohérence client** | Données client dupliquées | MDM (Customer Hub) |
| **Ordre des événements** | Events peuvent arriver désordonnés | Event ordering + idempotence |
| **Panne Claims** | Claims indisponible | Retry + DLQ |
| **Volume batch** | Trop de données à synchroniser | CDC incrémental |
| **Multi-canal** | Mobile vs Web différents besoins | BFF pattern |

---

## Ce que vous allez construire

Dans le **Sandbox**, vous allez :

1. **Implémenter** ces services mock
2. **Connecter** les services via API
3. **Publier** et **consommer** des événements
4. **Créer** des pipelines de données
5. **Gérer** les pannes et erreurs
6. **Observer** les flux en temps réel

Chaque module théorique sera accompagné de scénarios pratiques pour expérimenter ces concepts.

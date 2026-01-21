# Le Richardson Maturity Model

## Résumé

Le **Richardson Maturity Model (RMM)** est un modèle de maturité des APIs REST proposé par Leonard Richardson. Il définit 4 niveaux de maturité qui guident la conception d'APIs RESTful.

## Les 4 Niveaux

### Level 0 - Le Marais des POX (Plain Old XML)

À ce niveau, HTTP est utilisé comme simple tunnel de transport. Une seule URL, une seule méthode (souvent POST).

```
POST /api
{
  "action": "getQuote",
  "quoteId": "Q001"
}
```

**Problèmes** : Pas d'utilisation des capacités HTTP, difficile à cacher, pas de découvrabilité.

### Level 1 - Ressources

Introduction des **ressources** avec des URLs distinctes. Chaque entité a son endpoint.

```
POST /quotes/Q001
{
  "action": "get"
}

POST /policies/POL-001
{
  "action": "create"
}
```

**Amélioration** : Structure plus claire, mais HTTP pas encore pleinement utilisé.

### Level 2 - Verbes HTTP

Utilisation des **verbes HTTP** appropriés : GET, POST, PUT, DELETE, PATCH.

```
GET    /quotes/Q001          → Lecture
POST   /quotes               → Création
PUT    /quotes/Q001          → Mise à jour complète
PATCH  /quotes/Q001          → Mise à jour partielle
DELETE /quotes/Q001          → Suppression
```

**Codes de statut HTTP** utilisés correctement :
- `200 OK` : Succès
- `201 Created` : Ressource créée
- `204 No Content` : Suppression réussie
- `400 Bad Request` : Erreur client
- `404 Not Found` : Ressource inexistante
- `500 Internal Server Error` : Erreur serveur

### Level 3 - HATEOAS (Hypermedia)

**Hypermedia As The Engine Of Application State** : Les réponses incluent des liens vers les actions possibles.

```json
{
  "id": "Q001",
  "customer_id": "C001",
  "premium": 850.00,
  "status": "PENDING",
  "_links": {
    "self": { "href": "/quotes/Q001" },
    "accept": { "href": "/quotes/Q001/accept", "method": "POST" },
    "reject": { "href": "/quotes/Q001/reject", "method": "POST" },
    "customer": { "href": "/customers/C001" }
  }
}
```

**Avantages** :
- API auto-découvrable
- Le client n'a pas besoin de connaître les URLs
- Évolution plus facile de l'API

## Cas d'Usage Assurance

| Niveau | Quote Engine | Policy Admin |
|--------|-------------|--------------|
| 0 | POST /api avec action | POST /api avec action |
| 1 | POST /quotes/{id} | POST /policies/{id} |
| 2 | GET/POST/PUT /quotes | GET/POST/PUT/DELETE /policies |
| 3 | + liens vers accept, policy | + liens vers activate, renew |

## Recommandation

Pour un système d'assurance moderne :
- **Minimum Level 2** pour les APIs internes
- **Level 3 recommandé** pour les APIs partenaires (courtiers, comparateurs)

> **Note** : La plupart des "REST APIs" en production sont en réalité au niveau 2. Le niveau 3 (HATEOAS) apporte de la valeur mais augmente la complexité.

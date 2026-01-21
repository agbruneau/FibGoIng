# Versioning d'API

## Résumé

Le versioning d'API est essentiel pour faire évoluer une API sans casser les clients existants. Il existe plusieurs stratégies, chacune avec ses avantages et inconvénients.

## Pourquoi Versionner ?

- **Évolution** : Les besoins changent, l'API doit évoluer
- **Rétrocompatibilité** : Les anciens clients doivent continuer à fonctionner
- **Migration progressive** : Permettre une transition en douceur
- **Dépréciation** : Signaler les fonctionnalités qui seront retirées

## Stratégies de Versioning

### 1. Dans l'URL (Path)

La méthode la plus répandue et la plus simple.

```
GET /v1/quotes/Q001
GET /v2/quotes/Q001
```

**Avantages** :
- Très visible et explicite
- Facile à implémenter
- Cache-friendly

**Inconvénients** :
- L'URL n'est plus vraiment "l'identifiant de la ressource"
- Multiplication des routes

### 2. Dans le Header

Version spécifiée via un header HTTP custom.

```http
GET /quotes/Q001
Accept-Version: v2
```

Ou avec le header `Accept` :

```http
GET /quotes/Q001
Accept: application/vnd.assurance.v2+json
```

**Avantages** :
- URL propre
- Respecte mieux les principes REST

**Inconvénients** :
- Moins visible
- Plus complexe à tester dans un navigateur

### 3. Query Parameter

Version comme paramètre de requête.

```
GET /quotes/Q001?version=2
```

**Avantages** :
- Facile à ajouter
- Visible dans l'URL

**Inconvénients** :
- Pollue l'URL
- Peut être omis par erreur

## Recommandation pour l'Assurance

### API Internes (Entre Microservices)

```
Pas de version dans l'URL
Contrats stricts avec OpenAPI
Déploiements synchronisés
```

### API Partenaires (Courtiers, Comparateurs)

```
Version dans l'URL : /v1/, /v2/
Support de 2 versions simultanées
Dépréciation avec préavis (6 mois minimum)
```

## Règles d'Évolution

### Changements Rétrocompatibles (Pas de nouvelle version)

- ✅ Ajouter un nouveau endpoint
- ✅ Ajouter un champ optionnel à une réponse
- ✅ Ajouter un champ optionnel en entrée
- ✅ Rendre un champ obligatoire optionnel

### Changements Non-Rétrocompatibles (Nouvelle version)

- ❌ Supprimer un endpoint
- ❌ Supprimer un champ d'une réponse
- ❌ Rendre un champ optionnel obligatoire
- ❌ Changer le type d'un champ
- ❌ Changer la sémantique d'un champ

## Exemple de Migration

### Version 1 (Actuelle)

```json
// GET /v1/quotes/Q001
{
  "id": "Q001",
  "customer_id": "C001",
  "amount": 850.00,
  "status": "PENDING"
}
```

### Version 2 (Nouvelle)

```json
// GET /v2/quotes/Q001
{
  "id": "Q001",
  "customer": {
    "id": "C001",
    "name": "Jean Dupont"
  },
  "pricing": {
    "base_premium": 750.00,
    "taxes": 100.00,
    "total": 850.00
  },
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Stratégie de Migration

```
1. T+0  : Publier v2, v1 toujours supportée
2. T+3m : Annoncer dépréciation de v1
3. T+6m : Header "Deprecated: true" sur v1
4. T+12m: Retirer v1
```

## Dépréciation

### Headers de Dépréciation

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2024 23:59:59 GMT
Link: </v2/quotes>; rel="successor-version"
```

### Documentation

Toujours documenter clairement :
- Quelles versions sont supportées
- Date de fin de support
- Guide de migration vers la nouvelle version

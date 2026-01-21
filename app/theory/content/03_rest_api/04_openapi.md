# OpenAPI et Documentation

## Résumé

**OpenAPI** (anciennement Swagger) est le standard de facto pour documenter les APIs REST. C'est un fichier YAML ou JSON qui décrit complètement une API.

## Structure d'un Document OpenAPI

```yaml
openapi: 3.1.0
info:
  title: Quote Engine API
  description: API de gestion des devis d'assurance
  version: 1.0.0
  contact:
    name: Équipe API
    email: api@assurance.fr

servers:
  - url: https://api.assurance.fr/v1
    description: Production
  - url: https://api-staging.assurance.fr/v1
    description: Staging

paths:
  /quotes:
    get:
      summary: Liste les devis
      # ...
    post:
      summary: Crée un devis
      # ...

components:
  schemas:
    Quote:
      # ...
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

## Définir les Endpoints

### Opération GET

```yaml
paths:
  /quotes/{quote_id}:
    get:
      summary: Récupère un devis
      description: Retourne les détails d'un devis par son ID
      operationId: getQuote
      tags:
        - Quotes
      parameters:
        - name: quote_id
          in: path
          required: true
          schema:
            type: string
          description: ID du devis
          example: Q001
      responses:
        '200':
          description: Devis trouvé
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Quote'
        '404':
          description: Devis non trouvé
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
```

### Opération POST

```yaml
  /quotes:
    post:
      summary: Crée un devis
      operationId: createQuote
      tags:
        - Quotes
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QuoteRequest'
            example:
              customer_id: C001
              product: AUTO
              risk_data:
                age: 35
                zone: urbain
      responses:
        '201':
          description: Devis créé
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Quote'
          headers:
            Location:
              description: URL du devis créé
              schema:
                type: string
        '400':
          description: Données invalides
```

## Définir les Schemas

```yaml
components:
  schemas:
    Quote:
      type: object
      required:
        - id
        - customer_id
        - product
        - premium
        - status
      properties:
        id:
          type: string
          description: Identifiant unique du devis
          example: Q001
        customer_id:
          type: string
          description: ID du client
          example: C001
        product:
          type: string
          enum: [AUTO, HABITATION, MRH]
          description: Type de produit
        premium:
          type: number
          format: float
          description: Prime calculée
          example: 850.00
        status:
          type: string
          enum: [PENDING, ACCEPTED, REJECTED, EXPIRED]
        risk_data:
          $ref: '#/components/schemas/RiskData'
        created_at:
          type: string
          format: date-time
        expires_at:
          type: string
          format: date-time

    QuoteRequest:
      type: object
      required:
        - customer_id
        - product
      properties:
        customer_id:
          type: string
        product:
          type: string
          enum: [AUTO, HABITATION, MRH]
        risk_data:
          $ref: '#/components/schemas/RiskData'

    Error:
      type: object
      properties:
        code:
          type: string
        message:
          type: string
        details:
          type: array
          items:
            type: string
```

## Sécurité

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
    oauth2:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: /oauth/token
          scopes:
            quotes:read: Lire les devis
            quotes:write: Créer/modifier les devis

security:
  - bearerAuth: []
```

## Avantages d'OpenAPI

### Génération de Code

- **Serveur** : Génération de stubs (FastAPI, Spring, etc.)
- **Client** : SDKs dans plusieurs langages
- **Tests** : Génération de tests automatiques

### Documentation Interactive

- **Swagger UI** : Interface web pour tester l'API
- **ReDoc** : Documentation lisible
- **Postman** : Import direct

### Validation

- Validation des requêtes entrantes
- Validation des réponses
- Contrats entre équipes

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| Exemples | Toujours inclure des exemples réalistes |
| Descriptions | Décrire chaque champ clairement |
| Tags | Organiser les endpoints par domaine |
| operationId | Identifiant unique pour la génération de code |
| Versioning | Inclure la version dans info.version |

## Intégration avec FastAPI

FastAPI génère automatiquement la documentation OpenAPI :

```python
from fastapi import FastAPI

app = FastAPI(
    title="Quote Engine API",
    description="API de gestion des devis",
    version="1.0.0"
)

# Documentation disponible sur :
# - /docs (Swagger UI)
# - /redoc (ReDoc)
# - /openapi.json (Spec JSON)
```

# Authentification au Gateway

## Résumé

L'**authentification au Gateway** vérifie l'identité du client avant de router vers les services backend. C'est le point central pour la sécurité des APIs.

## Méthodes d'Authentification

### API Key

Simple clé partagée, idéale pour les partenaires B2B.

```http
GET /quotes/Q001
X-API-Key: sk_live_abc123def456
```

**Avantages :**
- Simple à implémenter
- Pas d'expiration automatique
- Facile à révoquer

**Inconvénients :**
- Pas de contexte utilisateur
- Doit être gardée secrète
- Pas de refresh automatique

**Usage :** Partenaires, applications serveur-à-serveur

### JWT (JSON Web Token)

Token signé contenant des informations (claims).

```http
GET /quotes/Q001
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Structure d'un JWT :
```
Header.Payload.Signature

Payload (claims):
{
  "sub": "user123",              // Subject (user ID)
  "iss": "https://auth.assurance.fr",  // Issuer
  "exp": 1642435200,             // Expiration
  "iat": 1642348800,             // Issued at
  "roles": ["courtier", "admin"],
  "partner_id": "COURTIER-001"
}
```

**Avantages :**
- Stateless (pas de lookup DB)
- Contient les claims (rôles, etc.)
- Standard largement adopté

**Inconvénients :**
- Taille du token
- Révocation complexe
- Sensible si clé compromise

### OAuth 2.0 / OIDC

Framework complet pour l'authentification et l'autorisation.

```
┌─────────┐     1. Auth Request    ┌─────────────────┐
│  Client │ ────────────────────► │ Authorization   │
│         │ ◄──────────────────── │ Server          │
│         │     2. Auth Code       │                 │
│         │ ────────────────────► │                 │
│         │     3. Token Request   │                 │
│         │ ◄──────────────────── │                 │
└─────────┘     4. Access Token    └─────────────────┘
      │
      │ 5. API Call + Token
      ▼
┌─────────────┐
│ API Gateway │ → Valide le token → Services
└─────────────┘
```

**Flows OAuth :**

| Flow | Usage |
|------|-------|
| Authorization Code | Apps web, mobile (avec PKCE) |
| Client Credentials | Machine-to-machine |
| Resource Owner Password | Legacy (déconseillé) |

### mTLS (Mutual TLS)

Authentification par certificat client.

```
Client                Gateway
  │                      │
  │ ──── ClientHello ──► │
  │ ◄── ServerHello ──── │
  │ ◄── Server Cert ──── │
  │ ◄── Cert Request ─── │  ← Gateway demande un cert client
  │ ──── Client Cert ──► │  ← Client présente son certificat
  │ ──── Verify ───────► │
  │ ◄── Verified ─────── │
```

**Usage :** APIs internes, haute sécurité, B2B critique

## Configuration Gateway

### Multi-méthodes selon le contexte

```yaml
authentication:
  routes:
    # APIs Partenaires : API Key
    - match: /partners/**
      auth:
        type: api_key
        header: X-API-Key
        lookup: redis  # Validation dans Redis

    # APIs Mobile : JWT
    - match: /mobile/**
      auth:
        type: jwt
        issuer: https://auth.assurance.fr
        audience: mobile-app
        jwks_uri: https://auth.assurance.fr/.well-known/jwks.json

    # APIs Internes : mTLS
    - match: /internal/**
      auth:
        type: mtls
        ca_cert: /certs/internal-ca.pem
        require_client_cert: true
```

## Validation JWT au Gateway

```python
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

JWKS_URL = "https://auth.assurance.fr/.well-known/jwks.json"
AUDIENCE = "assurance-api"
ISSUER = "https://auth.assurance.fr"

async def validate_token(credentials = Depends(security)):
    token = credentials.credentials

    try:
        # Récupère les clés publiques (cache recommandé)
        jwks = await fetch_jwks(JWKS_URL)

        # Valide et décode le token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER
        )

        return payload  # Claims disponibles pour la suite

    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

## Propagation de l'Identité

Une fois authentifié au gateway, l'identité est propagée aux services.

### Via Headers

```http
# Requête client
GET /quotes/Q001
Authorization: Bearer eyJ...

# Requête interne (gateway → service)
GET /quotes/Q001
X-User-Id: user123
X-Partner-Id: COURTIER-001
X-Roles: courtier,admin
X-Request-Id: req-abc123
```

### Via JWT interne

Le gateway génère un nouveau JWT pour les services internes.

```python
# Gateway génère un token interne
internal_token = create_internal_jwt({
    "sub": validated_claims["sub"],
    "roles": validated_claims["roles"],
    "partner_id": validated_claims["partner_id"],
    "exp": time.time() + 60  # Courte durée
})

# Propagé dans le header
headers["Authorization"] = f"Bearer {internal_token}"
```

## Cas Assurance

### Matrice d'authentification

| Client | Méthode | Détails |
|--------|---------|---------|
| App Mobile | OAuth 2.0 + PKCE | Token rafraîchi, biométrie |
| Portail Courtier | OAuth 2.0 + SAML | SSO avec l'entreprise courtier |
| Comparateurs | API Key | Key par partenaire, rate limited |
| Services internes | mTLS | Certificats gérés par infra |
| Batch/ETL | Service Account | Client Credentials flow |

### Exemple : Authentification Courtier

```yaml
# Configuration SSO courtier
sso:
  courtier_a:
    type: saml
    idp_metadata: https://courtier-a.com/saml/metadata
    sp_entity_id: assurance-api
    attribute_mapping:
      user_id: NameID
      email: http://schemas/email
      role: http://schemas/role

  courtier_b:
    type: oidc
    issuer: https://auth.courtier-b.com
    client_id: assurance-api
    scopes: [openid, profile, email]
```

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| HTTPS obligatoire | Jamais de credentials en clair |
| Rotation des clés | API Keys et secrets régulièrement changés |
| Audit logging | Logger toutes les authentifications |
| Fail secure | En cas de doute, rejeter |
| Least privilege | Donner le minimum de droits nécessaires |

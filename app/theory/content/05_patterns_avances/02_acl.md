# Anti-Corruption Layer (ACL)

## Objectif pédagogique

Protéger son domaine métier des systèmes legacy avec l'Anti-Corruption Layer.

## Le problème

Intégrer un système legacy sans polluer son nouveau design :

```
┌────────────────────┐      ┌────────────────────┐
│   Nouveau Système  │ ───▶ │   Legacy System    │
│   (Clean Design)   │      │   (Modèle ancien)  │
└────────────────────┘      └────────────────────┘
```

**Risques sans ACL :**
- Le nouveau système adopte les défauts du legacy
- Couplage fort avec le modèle ancien
- Migration future impossible

## La solution : ACL

```
┌────────────────────┐      ┌─────────┐      ┌────────────────────┐
│   Nouveau Système  │ ───▶ │   ACL   │ ───▶ │   Legacy System    │
│   (Clean Design)   │      │         │      │   (Modèle ancien)  │
└────────────────────┘      └─────────┘      └────────────────────┘
                                │
                         ┌──────┴──────┐
                         │ Traduction  │
                         │ Adaptation  │
                         │ Validation  │
                         └─────────────┘
```

## Cas concret : Migration PAS Legacy

### Le système legacy

```xml
<!-- API SOAP du vieux PAS -->
<soapenv:Envelope>
    <pol:GetContrat>
        <NumContrat>12345678</NumContrat>
    </pol:GetContrat>
</soapenv:Envelope>

<pol:ContratResponse>
    <NumContrat>12345678</NumContrat>
    <CodeProduit>AUTMRP</CodeProduit>
    <NumClient>987654</NumClient>
    <MontPrime>65000</MontPrime>  <!-- En centimes ! -->
    <StatutCtr>ACT</StatutCtr>
    <DtDebEff>20230201</DtDebEff>  <!-- Format YYYYMMDD -->
</pol:ContratResponse>
```

### Le nouveau modèle

```python
@dataclass
class Policy:
    number: str
    product: ProductType
    customer_id: str
    premium: Decimal
    status: PolicyStatus
    start_date: date
```

### L'ACL

```python
class LegacyPASAdapter:
    """Anti-Corruption Layer pour le PAS Legacy."""

    PRODUCT_MAPPING = {
        "AUTMRP": ProductType.AUTO,
        "HABMRH": ProductType.HABITATION,
        "MRHSTD": ProductType.MRH,
    }

    STATUS_MAPPING = {
        "ACT": PolicyStatus.ACTIVE,
        "SUS": PolicyStatus.SUSPENDED,
        "RES": PolicyStatus.CANCELLED,
        "EXP": PolicyStatus.EXPIRED,
    }

    def __init__(self, soap_client):
        self.client = soap_client

    async def get_policy(self, policy_number: str) -> Policy:
        """Récupère une police depuis le legacy et la traduit."""

        # Appel SOAP au legacy
        legacy_response = await self.client.call(
            "GetContrat",
            {"NumContrat": policy_number}
        )

        # Traduction vers notre modèle
        return self._translate_policy(legacy_response)

    def _translate_policy(self, legacy: dict) -> Policy:
        """Traduit une réponse legacy vers notre modèle."""

        return Policy(
            number=f"POL-{legacy['NumContrat']}",
            product=self.PRODUCT_MAPPING.get(
                legacy["CodeProduit"],
                ProductType.OTHER
            ),
            customer_id=f"C{legacy['NumClient']}",
            premium=Decimal(legacy["MontPrime"]) / 100,  # Centimes → Euros
            status=self.STATUS_MAPPING.get(
                legacy["StatutCtr"],
                PolicyStatus.UNKNOWN
            ),
            start_date=datetime.strptime(
                legacy["DtDebEff"], "%Y%m%d"
            ).date()
        )

    async def create_policy(self, policy: Policy) -> str:
        """Crée une police dans le legacy."""

        # Traduction inverse
        legacy_request = self._to_legacy_format(policy)

        # Appel legacy
        response = await self.client.call("CreerContrat", legacy_request)

        return response["NumContrat"]

    def _to_legacy_format(self, policy: Policy) -> dict:
        """Convertit notre modèle vers le format legacy."""

        product_reverse = {v: k for k, v in self.PRODUCT_MAPPING.items()}

        return {
            "CodeProduit": product_reverse.get(policy.product, "AUTRE"),
            "NumClient": policy.customer_id.replace("C", ""),
            "MontPrime": int(policy.premium * 100),
            "DtDebEff": policy.start_date.strftime("%Y%m%d"),
        }
```

## Pattern Strangler Fig

Migration progressive avec ACL :

```
Phase 1: Façade devant le legacy
┌────────┐     ┌─────┐     ┌────────┐
│ Client │ ──▶ │ ACL │ ──▶ │ Legacy │
└────────┘     └─────┘     └────────┘

Phase 2: Nouveau service pour certaines opérations
┌────────┐     ┌─────┐ ──▶ ┌────────┐
│ Client │ ──▶ │ ACL │     │ Legacy │
└────────┘     └──┬──┘     └────────┘
                  │
                  └──────▶ ┌─────────┐
                           │ Nouveau │
                           └─────────┘

Phase 3: Migration complète
┌────────┐     ┌─────────┐
│ Client │ ──▶ │ Nouveau │
└────────┘     └─────────┘
```

## Bonnes pratiques

### 1. Isoler complètement

```python
# ❌ Mauvais : modèle legacy qui fuit
class Policy:
    code_produit: str  # Naming legacy !
    mont_prime: int    # En centimes...

# ✅ Bon : modèle propre
class Policy:
    product: ProductType
    premium: Decimal
```

### 2. Logger les transformations

```python
def _translate_policy(self, legacy: dict) -> Policy:
    logger.debug(f"Translating legacy policy: {legacy['NumContrat']}")

    policy = Policy(...)

    logger.debug(f"Translated to: {policy}")
    return policy
```

### 3. Gérer les cas limites

```python
def _translate_status(self, legacy_status: str) -> PolicyStatus:
    if legacy_status in self.STATUS_MAPPING:
        return self.STATUS_MAPPING[legacy_status]

    logger.warning(f"Unknown legacy status: {legacy_status}")
    return PolicyStatus.UNKNOWN
```

## Exercice

Implémenter un ACL pour intégrer un service de notation externe qui retourne :

```json
{
  "score": "A+",
  "risk_level": "LOW",
  "factors": ["age:OK", "claims:WARN"]
}
```

Vers notre modèle :

```python
@dataclass
class RiskAssessment:
    score: int  # 0-100
    category: RiskCategory  # LOW, MEDIUM, HIGH
    factors: List[RiskFactor]
```

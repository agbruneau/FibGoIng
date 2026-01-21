"""Routes API pour les services mock d'assurance."""
from fastapi import APIRouter, HTTPException, Body
from typing import Optional
from pydantic import BaseModel

from app.mocks import (
    init_mock_services, get_service, registry,
    MockServiceError, get_mock_data
)

router = APIRouter()

# Initialiser les services au chargement du module
_initialized = False


def ensure_initialized():
    """S'assure que les services sont initialisés."""
    global _initialized
    if not _initialized:
        init_mock_services()
        _initialized = True


# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class QuoteRequest(BaseModel):
    customer_id: str
    product: str
    risk_data: dict = {}


class PolicyRequest(BaseModel):
    customer_id: str
    product: str
    quote_id: Optional[str] = None
    coverages: list = None
    premium: float = 0.0


class ClaimRequest(BaseModel):
    policy_number: str
    claim_type: str
    description: str
    incident_date: Optional[str] = None
    estimated_amount: Optional[float] = None


class InvoiceRequest(BaseModel):
    policy_number: str
    amount: float
    due_date: Optional[str] = None
    description: Optional[str] = None


class CustomerRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[dict] = None
    birth_date: Optional[str] = None


class ConfigureServiceRequest(BaseModel):
    latency: Optional[int] = None
    failure_rate: Optional[float] = None


class InjectFailureRequest(BaseModel):
    failure_rate: float = 1.0


class UpdateClaimStatusRequest(BaseModel):
    new_status: str
    note: Optional[str] = None


class RecordPaymentRequest(BaseModel):
    amount: float
    payment_method: str = "VIREMENT"
    reference: Optional[str] = None


# ============================================================
# ENDPOINTS GÉNÉRAUX
# ============================================================

@router.get("/services")
async def list_services():
    """Liste tous les services mock et leur statut."""
    ensure_initialized()
    return registry.get_all_stats()


@router.get("/services/{service_id}")
async def get_service_status(service_id: str):
    """Récupère le statut d'un service."""
    ensure_initialized()
    service = get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
    return service.get_stats()


@router.post("/services/{service_id}/configure")
async def configure_service(
    service_id: str,
    request: ConfigureServiceRequest
):
    """Configure un service (latence, taux de panne)."""
    ensure_initialized()
    service = get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    if request.latency is not None:
        service.config.latency_ms = max(0, request.latency)
    if request.failure_rate is not None:
        service.config.failure_rate = max(0.0, min(1.0, request.failure_rate))

    return service.get_stats()


@router.post("/services/{service_id}/inject-failure")
async def inject_failure(service_id: str, request: InjectFailureRequest):
    """Injecte des pannes dans un service."""
    ensure_initialized()
    service = get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    service.inject_failure(request.failure_rate)
    return {"message": f"Failure injected with rate {request.failure_rate}", "stats": service.get_stats()}


@router.post("/services/reset")
async def reset_all_services():
    """Réinitialise tous les services."""
    ensure_initialized()
    registry.reset_all()
    return {"message": "All services reset", "stats": registry.get_all_stats()}


# ============================================================
# QUOTE ENGINE
# ============================================================

@router.post("/quotes", status_code=201)
async def create_quote(request: QuoteRequest):
    """Crée un nouveau devis."""
    ensure_initialized()
    service = get_service("quote_engine")
    try:
        result = await service.create_quote(
            customer_id=request.customer_id,
            product=request.product,
            risk_data=request.risk_data
        )
        return result
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/quotes")
async def list_quotes(customer_id: Optional[str] = None):
    """Liste les devis."""
    ensure_initialized()
    service = get_service("quote_engine")
    try:
        return await service.list_quotes(customer_id=customer_id)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/quotes/{quote_id}")
async def get_quote(quote_id: str):
    """Récupère un devis."""
    ensure_initialized()
    service = get_service("quote_engine")
    try:
        return await service.get_quote(quote_id)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/quotes/{quote_id}/accept")
async def accept_quote(quote_id: str):
    """Accepte un devis."""
    ensure_initialized()
    service = get_service("quote_engine")
    try:
        return await service.accept_quote(quote_id)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# POLICY ADMIN
# ============================================================

@router.post("/policies", status_code=201)
async def create_policy(request: PolicyRequest):
    """Crée une nouvelle police."""
    ensure_initialized()
    service = get_service("policy_admin")
    try:
        return await service.create_policy(
            customer_id=request.customer_id,
            product=request.product,
            quote_id=request.quote_id,
            coverages=request.coverages,
            premium=request.premium
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/policies")
async def list_policies(
    customer_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Liste les polices."""
    ensure_initialized()
    service = get_service("policy_admin")
    try:
        return await service.list_policies(customer_id=customer_id, status=status)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/policies/{policy_number}")
async def get_policy(policy_number: str):
    """Récupère une police."""
    ensure_initialized()
    service = get_service("policy_admin")
    try:
        return await service.get_policy(policy_number)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/policies/{policy_number}/activate")
async def activate_policy(policy_number: str, start_date: Optional[str] = None):
    """Active une police."""
    ensure_initialized()
    service = get_service("policy_admin")
    try:
        return await service.activate_policy(policy_number, start_date)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/policies/{policy_number}", status_code=204)
async def delete_policy(policy_number: str):
    """Résilie une police."""
    ensure_initialized()
    service = get_service("policy_admin")
    try:
        await service.cancel_policy(policy_number, "Deleted via API")
        return None
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# CLAIMS
# ============================================================

@router.post("/claims", status_code=201)
async def create_claim(request: ClaimRequest):
    """Déclare un sinistre."""
    ensure_initialized()
    service = get_service("claims")
    try:
        return await service.create_claim(
            policy_number=request.policy_number,
            claim_type=request.claim_type,
            description=request.description,
            incident_date=request.incident_date,
            estimated_amount=request.estimated_amount
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/claims")
async def list_claims(
    policy_number: Optional[str] = None,
    status: Optional[str] = None
):
    """Liste les sinistres."""
    ensure_initialized()
    service = get_service("claims")
    try:
        return await service.list_claims(policy_number=policy_number, status=status)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/claims/{claim_number}")
async def get_claim(claim_number: str):
    """Récupère un sinistre."""
    ensure_initialized()
    service = get_service("claims")
    try:
        return await service.get_claim(claim_number)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/claims/{claim_number}/status")
async def update_claim_status(
    claim_number: str,
    request: UpdateClaimStatusRequest
):
    """Met à jour le statut d'un sinistre."""
    ensure_initialized()
    service = get_service("claims")
    try:
        return await service.update_status(claim_number, request.new_status, request.note)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# BILLING
# ============================================================

@router.post("/invoices", status_code=201)
async def create_invoice(request: InvoiceRequest):
    """Crée une facture."""
    ensure_initialized()
    service = get_service("billing")
    try:
        return await service.create_invoice(
            policy_number=request.policy_number,
            amount=request.amount,
            due_date=request.due_date,
            description=request.description
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/invoices/policy/{policy_number}")
async def get_policy_invoices(policy_number: str):
    """Récupère les factures d'une police."""
    ensure_initialized()
    service = get_service("billing")
    try:
        return await service.list_invoices(policy_number=policy_number)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/invoices/{invoice_number}")
async def get_invoice(invoice_number: str):
    """Récupère une facture."""
    ensure_initialized()
    service = get_service("billing")
    try:
        return await service.get_invoice(invoice_number)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/invoices/{invoice_number}/payment")
async def record_payment(
    invoice_number: str,
    request: RecordPaymentRequest
):
    """Enregistre un paiement."""
    ensure_initialized()
    service = get_service("billing")
    try:
        return await service.record_payment(
            invoice_number=invoice_number,
            amount=request.amount,
            payment_method=request.payment_method,
            reference=request.reference
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# CUSTOMERS
# ============================================================

@router.post("/customers", status_code=201)
async def create_customer(request: CustomerRequest):
    """Crée un client."""
    ensure_initialized()
    service = get_service("customer_hub")
    try:
        return await service.create_customer(
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address,
            birth_date=request.birth_date
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/customers")
async def list_customers(
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """Liste les clients."""
    ensure_initialized()
    service = get_service("customer_hub")
    try:
        return await service.list_customers(status=status, search=search)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Récupère un client."""
    ensure_initialized()
    service = get_service("customer_hub")
    try:
        return await service.get_customer(customer_id)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, updates: dict = Body(...)):
    """Met à jour un client."""
    ensure_initialized()
    service = get_service("customer_hub")
    try:
        return await service.update_customer(customer_id, **updates)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/customers/{customer_id}", status_code=204)
async def delete_customer(customer_id: str):
    """Désactive un client."""
    ensure_initialized()
    service = get_service("customer_hub")
    try:
        await service.delete_customer(customer_id)
        return None
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# EXTERNAL RATING
# ============================================================

@router.get("/rates/{product}")
async def get_rate(product: str, age: int = 30, zone: str = "B", claims_history: int = 0):
    """Obtient un tarif externe."""
    ensure_initialized()
    service = get_service("external_rating")
    try:
        return await service.get_rate(
            product=product,
            risk_profile={"age": age, "zone": zone, "claims_history": claims_history}
        )
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/rates/{product}/market")
async def get_market_rates(product: str):
    """Obtient les tarifs du marché."""
    ensure_initialized()
    service = get_service("external_rating")
    try:
        return await service.get_market_rates(product)
    except MockServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ============================================================
# DONNÉES MOCK BRUTES
# ============================================================

@router.get("/data")
async def get_all_mock_data():
    """Récupère toutes les données mock."""
    return get_mock_data()

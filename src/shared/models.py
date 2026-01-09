"""
AgentMeshKafka - Pydantic Models
=================================
Modèles de données générés depuis les schémas Avro.
Voir schemas/ et docs/02-DataContracts.md.

Ces modèles assurent la validation structurelle côté Python
avant la sérialisation Avro.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums (correspondant aux types Avro enum)
# =============================================================================

class EmploymentStatus(str, Enum):
    """Statut d'emploi du demandeur."""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    UNEMPLOYED = "UNEMPLOYED"


class RiskLevel(str, Enum):
    """Catégorie de risque basée sur le score."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionStatus(str, Enum):
    """Statut de la décision finale."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


# =============================================================================
# Models (correspondant aux types Avro record)
# =============================================================================

class LoanApplication(BaseModel):
    """
    Demande de prêt soumise.
    
    Topic: finance.loan.application.v1
    Schema: schemas/loan_application.avsc
    """
    
    application_id: str = Field(..., description="UUID unique de la demande de prêt")
    timestamp: int = Field(..., description="Horodatage de la soumission (epoch ms)")
    applicant_id: str = Field(..., description="Identifiant unique du demandeur")
    amount_requested: float = Field(..., gt=0, description="Montant du prêt demandé")
    currency: str = Field(default="USD", description="Devise du montant (ISO 4217)")
    declared_monthly_income: float = Field(..., gt=0, description="Revenu mensuel déclaré")
    employment_status: EmploymentStatus = Field(..., description="Statut d'emploi")
    existing_debts: float = Field(default=0.0, ge=0, description="Dettes existantes")
    loan_purpose: Optional[str] = Field(default=None, description="Motif du prêt")
    metadata: dict[str, str] = Field(default_factory=dict, description="Métadonnées")
    
    class Config:
        use_enum_values = True


class RiskAssessment(BaseModel):
    """
    Évaluation de risque complétée.
    
    Topic: risk.scoring.result.v1
    Schema: schemas/risk_assessment.avsc
    """
    
    application_id: str = Field(..., description="UUID de la demande analysée")
    assessment_id: str = Field(..., description="UUID unique de cette évaluation")
    timestamp: int = Field(..., description="Horodatage de l'évaluation")
    risk_score: int = Field(..., ge=0, le=100, description="Score de risque 0-100")
    risk_category: RiskLevel = Field(..., description="Catégorie de risque")
    debt_to_income_ratio: float = Field(..., ge=0, description="Ratio DTI calculé")
    rationale: str = Field(..., description="Justification en langage naturel")
    checked_policies: list[str] = Field(default_factory=list, description="Politiques consultées")
    confidence_score: float = Field(default=0.0, ge=0, le=1, description="Score de confiance")
    chain_of_thought: Optional[str] = Field(default=None, description="Trace ReAct")
    processing_time_ms: int = Field(default=0, ge=0, description="Temps de traitement")
    model_used: str = Field(default="claude-opus-4.5", description="Modèle LLM utilisé")
    
    class Config:
        use_enum_values = True


class LoanDecision(BaseModel):
    """
    Décision finale de prêt.
    
    Topic: finance.loan.decision.v1
    Schema: schemas/loan_decision.avsc
    """
    
    application_id: str = Field(..., description="UUID de la demande")
    decision_id: str = Field(..., description="UUID unique de cette décision")
    assessment_id: str = Field(..., description="UUID de l'évaluation associée")
    decision_timestamp: int = Field(..., description="Horodatage de la décision")
    status: DecisionStatus = Field(..., description="Statut de la décision")
    approved_amount: Optional[float] = Field(default=None, description="Montant approuvé")
    interest_rate: Optional[float] = Field(default=None, description="Taux d'intérêt proposé")
    decision_rationale: str = Field(..., description="Explication pour le client")
    rejection_reasons: list[str] = Field(default_factory=list, description="Raisons de rejet")
    risk_score_at_decision: int = Field(..., ge=0, le=100, description="Score au moment de la décision")
    decided_by: str = Field(default="agent-loan-officer", description="Identifiant du décideur")
    requires_human_approval: bool = Field(default=False, description="Nécessite validation humaine")
    
    class Config:
        use_enum_values = True

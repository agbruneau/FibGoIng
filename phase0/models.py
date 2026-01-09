"""
Phase 0 - Modèles de données simplifiés
========================================
Modèles Pydantic pour validation des données.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums
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
# Models
# =============================================================================

class LoanApplication(BaseModel):
    """Demande de prêt soumise."""
    
    application_id: str = Field(..., description="UUID unique de la demande")
    applicant_id: str = Field(..., description="Identifiant du demandeur")
    amount_requested: float = Field(..., gt=0, description="Montant du prêt demandé")
    currency: str = Field(default="USD", description="Devise")
    declared_monthly_income: float = Field(..., gt=0, description="Revenu mensuel déclaré")
    employment_status: EmploymentStatus = Field(..., description="Statut d'emploi")
    existing_debts: float = Field(default=0.0, ge=0, description="Dettes existantes")
    loan_purpose: Optional[str] = Field(default=None, description="Motif du prêt")
    
    class Config:
        use_enum_values = True


class RiskAssessment(BaseModel):
    """Évaluation de risque complétée."""
    
    application_id: str = Field(..., description="UUID de la demande analysée")
    assessment_id: str = Field(..., description="UUID unique de cette évaluation")
    risk_score: int = Field(..., ge=0, le=100, description="Score de risque 0-100")
    risk_category: RiskLevel = Field(..., description="Catégorie de risque")
    debt_to_income_ratio: float = Field(..., ge=0, description="Ratio DTI calculé")
    rationale: str = Field(..., description="Justification en langage naturel")
    
    class Config:
        use_enum_values = True


class LoanDecision(BaseModel):
    """Décision finale de prêt."""
    
    application_id: str = Field(..., description="UUID de la demande")
    decision_id: str = Field(..., description="UUID unique de cette décision")
    status: DecisionStatus = Field(..., description="Statut de la décision")
    approved_amount: Optional[float] = Field(default=None, description="Montant approuvé")
    interest_rate: Optional[float] = Field(default=None, description="Taux d'intérêt proposé")
    decision_rationale: str = Field(..., description="Explication pour le client")
    risk_score_at_decision: int = Field(..., ge=0, le=100, description="Score au moment de la décision")
    
    class Config:
        use_enum_values = True

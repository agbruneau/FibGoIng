"""
Phase 3 - Tests Unitaires des Modèles (L1)
============================================
Tests déterministes pour les modèles Pydantic.
"""

import pytest
from src.shared.models import (
    LoanApplication,
    RiskAssessment,
    LoanDecision,
    EmploymentStatus,
    RiskLevel,
    DecisionStatus,
)


class TestLoanApplication:
    """Tests pour le modèle LoanApplication."""
    
    def test_valid_application(self):
        """Test création d'une demande valide."""
        app = LoanApplication(
            application_id="test-001",
            applicant_id="CUST-001",
            amount_requested=50000,
            currency="USD",
            declared_monthly_income=5000,
            employment_status=EmploymentStatus.FULL_TIME,
            existing_debts=10000,
        )
        
        assert app.application_id == "test-001"
        assert app.amount_requested == 50000
        assert app.employment_status == EmploymentStatus.FULL_TIME
    
    def test_invalid_amount(self):
        """Test rejet d'un montant invalide."""
        with pytest.raises(Exception):
            LoanApplication(
                application_id="test-002",
                applicant_id="CUST-002",
                amount_requested=-1000,  # Montant négatif
                declared_monthly_income=5000,
                employment_status=EmploymentStatus.FULL_TIME,
            )
    
    def test_default_currency(self):
        """Test valeur par défaut pour la devise."""
        app = LoanApplication(
            application_id="test-003",
            applicant_id="CUST-003",
            amount_requested=50000,
            declared_monthly_income=5000,
            employment_status=EmploymentStatus.FULL_TIME,
        )
        
        assert app.currency == "USD"


class TestRiskAssessment:
    """Tests pour le modèle RiskAssessment."""
    
    def test_valid_assessment(self):
        """Test création d'une évaluation valide."""
        assessment = RiskAssessment(
            application_id="test-001",
            assessment_id="assess-001",
            risk_score=45,
            risk_category=RiskLevel.MEDIUM,
            debt_to_income_ratio=35.5,
            rationale="Score modéré basé sur DTI acceptable",
        )
        
        assert assessment.risk_score == 45
        assert assessment.risk_category == RiskLevel.MEDIUM
        assert assessment.debt_to_income_ratio == 35.5
    
    def test_invalid_risk_score(self):
        """Test rejet d'un score invalide."""
        with pytest.raises(Exception):
            RiskAssessment(
                application_id="test-002",
                assessment_id="assess-002",
                risk_score=150,  # Score > 100
                risk_category=RiskLevel.MEDIUM,
                debt_to_income_ratio=35.5,
                rationale="Test",
            )


class TestLoanDecision:
    """Tests pour le modèle LoanDecision."""
    
    def test_valid_decision(self):
        """Test création d'une décision valide."""
        decision = LoanDecision(
            application_id="test-001",
            decision_id="dec-001",
            status=DecisionStatus.APPROVED,
            approved_amount=50000,
            interest_rate=5.5,
            decision_rationale="Approuvé - Score de risque faible",
            risk_score_at_decision=15,
        )
        
        assert decision.status == DecisionStatus.APPROVED
        assert decision.approved_amount == 50000
        assert decision.interest_rate == 5.5

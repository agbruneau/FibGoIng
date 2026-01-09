"""
Tests unitaires pour les modèles Pydantic.
==========================================
Vérifie la validation structurelle des données.
"""

import pytest
from pydantic import ValidationError

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
        """Test création d'une application valide."""
        app = LoanApplication(
            application_id="APP-001",
            timestamp=1704067200000,
            applicant_id="CUST-123",
            amount_requested=50000.0,
            declared_monthly_income=5000.0,
            employment_status=EmploymentStatus.FULL_TIME,
        )
        
        assert app.application_id == "APP-001"
        assert app.amount_requested == 50000.0
        assert app.currency == "USD"  # Default
        assert app.existing_debts == 0.0  # Default
    
    def test_invalid_amount_zero(self):
        """Test rejet si montant <= 0."""
        with pytest.raises(ValidationError):
            LoanApplication(
                application_id="APP-002",
                timestamp=1704067200000,
                applicant_id="CUST-123",
                amount_requested=0,  # Invalid
                declared_monthly_income=5000.0,
                employment_status=EmploymentStatus.FULL_TIME,
            )
    
    def test_invalid_income_negative(self):
        """Test rejet si revenu négatif."""
        with pytest.raises(ValidationError):
            LoanApplication(
                application_id="APP-003",
                timestamp=1704067200000,
                applicant_id="CUST-123",
                amount_requested=50000.0,
                declared_monthly_income=-1000.0,  # Invalid
                employment_status=EmploymentStatus.FULL_TIME,
            )
    
    def test_all_employment_statuses(self):
        """Test tous les statuts d'emploi."""
        for status in EmploymentStatus:
            app = LoanApplication(
                application_id=f"APP-{status.value}",
                timestamp=1704067200000,
                applicant_id="CUST-123",
                amount_requested=50000.0,
                declared_monthly_income=5000.0,
                employment_status=status,
            )
            assert app.employment_status == status


class TestRiskAssessment:
    """Tests pour le modèle RiskAssessment."""
    
    def test_valid_assessment(self):
        """Test création d'une évaluation valide."""
        assessment = RiskAssessment(
            application_id="APP-001",
            assessment_id="ASS-001",
            timestamp=1704067200000,
            risk_score=45,
            risk_category=RiskLevel.MEDIUM,
            debt_to_income_ratio=35.5,
            rationale="DTI acceptable selon la politique 2.1",
            checked_policies=["Policy-2.1"],
        )
        
        assert assessment.risk_score == 45
        assert assessment.risk_category == RiskLevel.MEDIUM
    
    def test_risk_score_bounds(self):
        """Test limites du score (0-100)."""
        # Score valide à la limite basse
        assessment = RiskAssessment(
            application_id="APP-001",
            assessment_id="ASS-001",
            timestamp=1704067200000,
            risk_score=0,
            risk_category=RiskLevel.LOW,
            debt_to_income_ratio=10.0,
            rationale="Risque minimal",
        )
        assert assessment.risk_score == 0
        
        # Score invalide > 100
        with pytest.raises(ValidationError):
            RiskAssessment(
                application_id="APP-001",
                assessment_id="ASS-001",
                timestamp=1704067200000,
                risk_score=150,  # Invalid
                risk_category=RiskLevel.CRITICAL,
                debt_to_income_ratio=10.0,
                rationale="Test",
            )


class TestLoanDecision:
    """Tests pour le modèle LoanDecision."""
    
    def test_approved_decision(self):
        """Test décision approuvée."""
        decision = LoanDecision(
            application_id="APP-001",
            decision_id="DEC-001",
            assessment_id="ASS-001",
            decision_timestamp=1704067200000,
            status=DecisionStatus.APPROVED,
            approved_amount=50000.0,
            interest_rate=7.5,
            decision_rationale="Demande approuvée - risque faible",
            risk_score_at_decision=15,
        )
        
        assert decision.status == DecisionStatus.APPROVED
        assert decision.approved_amount == 50000.0
        assert decision.rejection_reasons == []
    
    def test_rejected_decision(self):
        """Test décision rejetée."""
        decision = LoanDecision(
            application_id="APP-002",
            decision_id="DEC-002",
            assessment_id="ASS-002",
            decision_timestamp=1704067200000,
            status=DecisionStatus.REJECTED,
            decision_rationale="Demande rejetée - DTI trop élevé",
            rejection_reasons=["DTI > 50%", "Historique de crédit insuffisant"],
            risk_score_at_decision=85,
        )
        
        assert decision.status == DecisionStatus.REJECTED
        assert decision.approved_amount is None
        assert len(decision.rejection_reasons) == 2

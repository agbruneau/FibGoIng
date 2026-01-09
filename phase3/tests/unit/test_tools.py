"""
Phase 3 - Tests Unitaires des Outils (L1)
==========================================
Tests déterministes pour les outils des agents.
"""

import pytest


def calculate_debt_ratio(income: float, existing_debts: float, new_loan_amount: float) -> float:
    """
    Calcule le ratio dette/revenu (DTI).
    
    Utilisé par l'Agent Risk.
    """
    if income <= 0:
        return 100.0
    
    estimated_monthly_payment = new_loan_amount * 0.01
    total_monthly_debt = existing_debts + estimated_monthly_payment
    dti = (total_monthly_debt / income) * 100
    return round(dti, 2)


def categorize_risk(score: int) -> str:
    """
    Catégorise un score de risque.
    
    Utilisé par l'Agent Risk.
    """
    if score < 20:
        return "LOW"
    elif score < 50:
        return "MEDIUM"
    elif score < 80:
        return "HIGH"
    else:
        return "CRITICAL"


class TestCalculateDebtRatio:
    """Tests pour le calcul du ratio dette/revenu."""
    
    def test_normal_case(self):
        """Test cas normal."""
        dti = calculate_debt_ratio(income=5000, existing_debts=1000, new_loan_amount=50000)
        # (1000 + 500) / 5000 * 100 = 30.0
        assert dti == 30.0
    
    def test_zero_income(self):
        """Test avec revenu zéro."""
        dti = calculate_debt_ratio(income=0, existing_debts=1000, new_loan_amount=50000)
        assert dti == 100.0  # Risque maximum
    
    def test_no_existing_debts(self):
        """Test sans dettes existantes."""
        dti = calculate_debt_ratio(income=5000, existing_debts=0, new_loan_amount=50000)
        # (0 + 500) / 5000 * 100 = 10.0
        assert dti == 10.0
    
    def test_high_dti(self):
        """Test avec DTI élevé."""
        dti = calculate_debt_ratio(income=3000, existing_debts=2000, new_loan_amount=100000)
        # (2000 + 1000) / 3000 * 100 = 100.0
        assert dti == 100.0


class TestCategorizeRisk:
    """Tests pour la catégorisation du risque."""
    
    def test_low_risk(self):
        """Test risque faible."""
        assert categorize_risk(15) == "LOW"
        assert categorize_risk(0) == "LOW"
        assert categorize_risk(19) == "LOW"
    
    def test_medium_risk(self):
        """Test risque moyen."""
        assert categorize_risk(25) == "MEDIUM"
        assert categorize_risk(49) == "MEDIUM"
    
    def test_high_risk(self):
        """Test risque élevé."""
        assert categorize_risk(60) == "HIGH"
        assert categorize_risk(79) == "HIGH"
    
    def test_critical_risk(self):
        """Test risque critique."""
        assert categorize_risk(85) == "CRITICAL"
        assert categorize_risk(100) == "CRITICAL"

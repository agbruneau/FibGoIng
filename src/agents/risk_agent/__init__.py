"""
Risk Agent - L'Analyste
========================
Identifiant Service: agent-risk-analyst
Modèle: Claude Opus 4.5 (Température: 0.2)

Rôle: Évaluer la solvabilité du demandeur via RAG sur les politiques de crédit.

Input: Topic finance.loan.application.v1
Output: Topic risk.scoring.result.v1

Voir docs/03-AgentSpecs.md Section 3 pour les spécifications complètes.
"""

from .main import RiskAgent

__all__ = ["RiskAgent"]

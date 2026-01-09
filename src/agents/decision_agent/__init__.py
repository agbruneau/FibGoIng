"""
Decision Agent - Le Décideur
=============================
Identifiant Service: agent-loan-officer
Modèle: Claude 3.5 Sonnet (Température: 0.1)

Rôle: Prendre la décision finale d'approbation ou de rejet basée sur l'analyse de risque.

Input: Topic risk.scoring.result.v1
Output: Topic finance.loan.decision.v1

Voir docs/03-AgentSpecs.md Section 4 pour les spécifications complètes.
"""

from .main import DecisionAgent

__all__ = ["DecisionAgent"]

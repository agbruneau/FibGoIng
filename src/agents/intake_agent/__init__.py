"""
Intake Agent - Le Contrôleur
=============================
Identifiant Service: agent-intake-service
Modèle: Claude 3.5 Haiku (Température: 0.0)

Rôle: Nettoyage, enrichissement et validation sémantique de la demande initiale.

Input: API REST (simulateur client) ou fichier CSV ingéré
Output: Topic finance.loan.application.v1

Voir docs/03-AgentSpecs.md Section 2 pour les spécifications complètes.
"""

from .main import IntakeAgent

__all__ = ["IntakeAgent"]

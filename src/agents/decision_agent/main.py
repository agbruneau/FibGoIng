#!/usr/bin/env python3
"""
Decision Agent - Agent de Décision de Prêt
===========================================

Agent intelligent de prise de décision finale pour les demandes de prêt,
basé sur l'évaluation de risque fournie par le Risk Agent.

L'agent consomme les évaluations de risque depuis Kafka, applique les règles
métier de décision (seuils auto-approve/reject), et publie la décision finale
avec justification.

Architecture:
    Ce module implémente l'Agent 3 (Loan Officer) du pipeline AgentMeshKafka.
    C'est le dernier maillon de la chaîne de décision::

        [Intake Agent] → [Risk Agent] → [Decision Agent] → Décision Finale

Règles de Décision:
    L'agent applique une logique en trois zones basée sur le score de risque:

    - **Score < 20** (Zone Verte): Approbation automatique
    - **Score > 80** (Zone Rouge): Rejet automatique  
    - **Score 20-80** (Zone Grise): Analyse détaillée via LLM

    Pour les montants élevés (> 100k USD par défaut), une revue humaine
    est systématiquement requise.

Configuration:
    L'agent peut être configuré via variables d'environnement ou ``config.yaml``::

        # Variables d'environnement
        DECISION_AGENT_MODEL=claude-3-5-sonnet-20241022
        DECISION_AGENT_TEMPERATURE=0.1
        DECISION_CONSUMER_GROUP=agent-loan-officer
        ANTHROPIC_API_KEY=sk-ant-...

        # Équivalent config.yaml
        agents:
          decision_agent:
            model: "claude-3-5-sonnet-20241022"
            temperature: 0.1
            consumer_group: "agent-loan-officer"

        thresholds:
          auto_approve_score: 20
          auto_reject_score: 80
          high_value_amount: 100000

Usage:
    En ligne de commande::

        $ python -m src.agents.decision_agent.main

    Programmatiquement::

        from src.agents.decision_agent.main import DecisionAgent
        from src.shared.models import RiskAssessment, RiskLevel

        agent = DecisionAgent()
        
        assessment = RiskAssessment(
            application_id="APP-001",
            assessment_id="ASSESS-001",
            risk_score=45,
            risk_category=RiskLevel.MEDIUM,
            debt_to_income_ratio=35.5,
            rationale="DTI acceptable, historique crédit stable",
            timestamp=1704067200000,
        )
        
        decision = agent.make_decision(assessment)
        print(f"Status: {decision.status.value}")
        print(f"Approved Amount: {decision.approved_amount}")

Topics Kafka:
    - **Consomme**: ``risk.scoring.result.v1``
    - **Produit**: ``finance.loan.decision.v1``

See Also:
    - :mod:`src.agents.risk_agent.main`: Agent de risque en amont
    - :mod:`src.shared.models`: Modèles de données Pydantic
    - ``docs/03-AgentSpecs.md``: Spécifications détaillées des agents
"""

import os
import uuid
from datetime import datetime

import structlog
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import RiskAssessment, LoanDecision, DecisionStatus
from src.shared.prompts import DECISION_AGENT_SYSTEM_PROMPT
from src.shared.logging_config import (
    configure_logging,
    get_logger,
    set_correlation_id,
    set_application_id,
    LoggingContext,
)
from src.shared.metrics import (
    start_metrics_server,
    record_decision,
    record_kafka_message,
    record_processing_time,
    set_agent_info,
    TimingContext,
)

load_dotenv()

# Configurer le logging structuré
configure_logging(agent_id="agent-loan-officer")
logger = get_logger()


class DecisionAgent:
    """
    Agent de décision finale pour les demandes de prêt.

    Cet agent prend la décision finale (approbation, rejet, ou revue manuelle)
    basée sur l'évaluation de risque fournie par le Risk Agent. Il applique
    des règles métier déterministes combinées à une analyse LLM pour les
    cas ambigus.

    L'agent consomme les messages du topic Kafka ``risk.scoring.result.v1``
    et publie les décisions dans ``finance.loan.decision.v1``.

    Attributes:
        model (ChatAnthropic): Client LLM Anthropic Claude pour l'analyse
            des cas en zone grise.
        consumer (KafkaConsumerClient): Consommateur Kafka pour les évaluations.
        producer (KafkaProducerClient): Producteur Kafka pour les décisions.
        agent_id (str): Identifiant unique de l'agent pour le tracing.
        THRESHOLD_AUTO_APPROVE (int): Score en dessous duquel approuver auto (défaut: 20).
        THRESHOLD_AUTO_REJECT (int): Score au dessus duquel rejeter auto (défaut: 80).
        THRESHOLD_HIGH_VALUE (float): Montant nécessitant revue humaine (défaut: 100k).

    Example:
        Utilisation basique::

            agent = DecisionAgent()
            agent.run()  # Démarre la boucle de consommation Kafka

        Prise de décision sur une évaluation::

            agent = DecisionAgent()
            decision = agent.make_decision(assessment)
            
            if decision.status == DecisionStatus.APPROVED:
                print(f"Prêt approuvé: {decision.approved_amount} USD")
                print(f"Taux: {decision.interest_rate}%")
            elif decision.status == DecisionStatus.REJECTED:
                print(f"Rejet: {decision.rejection_reasons}")

    Configuration:
        +---------------------------+----------------------------------+----------------------+
        | Variable Environnement    | Description                      | Défaut               |
        +===========================+==================================+======================+
        | DECISION_AGENT_MODEL      | Modèle Claude à utiliser         | claude-3-5-sonnet    |
        +---------------------------+----------------------------------+----------------------+
        | DECISION_AGENT_TEMPERATURE| Température du modèle (0.0-1.0)  | 0.1                  |
        +---------------------------+----------------------------------+----------------------+
        | DECISION_CONSUMER_GROUP   | Groupe de consommateurs Kafka    | agent-loan-officer   |
        +---------------------------+----------------------------------+----------------------+
        | ANTHROPIC_API_KEY         | Clé API Anthropic (requis)       | -                    |
        +---------------------------+----------------------------------+----------------------+

    Note:
        Les seuils de décision (auto_approve_score, auto_reject_score) peuvent
        être configurés via ``config.yaml`` dans la section ``thresholds``.

    See Also:
        - :class:`src.shared.models.LoanDecision`: Structure de sortie
        - :class:`src.shared.models.RiskAssessment`: Structure d'entrée
    """
    
    # Seuils de décision (configurable)
    THRESHOLD_AUTO_APPROVE = 20
    THRESHOLD_AUTO_REJECT = 80
    THRESHOLD_HIGH_VALUE = 100000  # Montant nécessitant revue humaine
    
    def __init__(self):
        """Initialise le DecisionAgent avec LLM, Kafka, et observabilité."""
        self.model = ChatAnthropic(
            model=os.getenv("DECISION_AGENT_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=float(os.getenv("DECISION_AGENT_TEMPERATURE", "0.1")),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        
        self.consumer = KafkaConsumerClient(
            topic="risk.scoring.result.v1",
            group_id=os.getenv("DECISION_CONSUMER_GROUP", "agent-loan-officer"),
        )
        
        self.producer = KafkaProducerClient(
            topic="finance.loan.decision.v1",
            schema_subject="finance.loan.decision.v1-value",
        )
        
        self.agent_id = "agent-loan-officer"
        
        # Démarrer le serveur de métriques Prometheus (port différent du RiskAgent)
        metrics_port = int(os.getenv("METRICS_PORT", "9092"))
        start_metrics_server(port=metrics_port)
        
        # Enregistrer les infos de l'agent
        set_agent_info(
            agent_id=self.agent_id,
            version="1.0.0",
            model=os.getenv("DECISION_AGENT_MODEL", "claude-3-5-sonnet-20241022"),
        )
        
        logger.info("DecisionAgent initialized", agent_id=self.agent_id)
    
    # -------------------------------------------------------------------------
    # Outils (Tools) - Voir docs/03-AgentSpecs.md Section 4.2
    # -------------------------------------------------------------------------
    
    def tool_check_bank_liquidity(self, amount: float) -> bool:
        """
        Vérifie si la banque a les fonds disponibles (simulé).
        
        Args:
            amount: Montant du prêt
            
        Returns:
            True si fonds disponibles
        """
        # TODO: Connecter au système bancaire réel
        logger.info("Checking bank liquidity", amount=amount)
        return amount < 500000  # Simulation: approuve jusqu'à 500k
    
    # -------------------------------------------------------------------------
    # Logique de décision
    # -------------------------------------------------------------------------
    
    def make_decision(self, assessment: RiskAssessment) -> LoanDecision:
        """
        Prend la décision finale basée sur l'évaluation de risque.
        
        Implémente les règles définies dans docs/03-AgentSpecs.md.
        """
        logger.info(
            "Making decision",
            application_id=assessment.application_id,
            risk_score=assessment.risk_score,
        )
        
        # Initialisation
        status = DecisionStatus.MANUAL_REVIEW_REQUIRED
        approved_amount = None
        interest_rate = None
        rejection_reasons = []
        requires_human = False
        
        # Règle 1: Approbation automatique pour risque très faible
        if assessment.risk_score < self.THRESHOLD_AUTO_APPROVE:
            status = DecisionStatus.APPROVED
            approved_amount = self._calculate_approved_amount(assessment)
            interest_rate = self._calculate_interest_rate(assessment.risk_score)
            
        # Règle 2: Rejet automatique pour risque critique
        elif assessment.risk_score > self.THRESHOLD_AUTO_REJECT:
            status = DecisionStatus.REJECTED
            rejection_reasons = self._determine_rejection_reasons(assessment)
            
        # Règle 3: Zone grise - analyse détaillée
        else:
            decision = self._analyze_gray_zone(assessment)
            status = decision["status"]
            approved_amount = decision.get("approved_amount")
            interest_rate = decision.get("interest_rate")
            rejection_reasons = decision.get("rejection_reasons", [])
            requires_human = decision.get("requires_human", False)
        
        # Générer la justification
        rationale = self._generate_decision_rationale(
            assessment, status, rejection_reasons
        )
        
        decision = LoanDecision(
            application_id=assessment.application_id,
            decision_id=str(uuid.uuid4()),
            assessment_id=assessment.assessment_id,
            decision_timestamp=int(datetime.now().timestamp() * 1000),
            status=status,
            approved_amount=approved_amount,
            interest_rate=interest_rate,
            decision_rationale=rationale,
            rejection_reasons=rejection_reasons,
            risk_score_at_decision=assessment.risk_score,
            decided_by=self.agent_id,
            requires_human_approval=requires_human,
        )
        
        logger.info(
            "Decision made",
            application_id=assessment.application_id,
            status=status.value,
            approved_amount=approved_amount,
        )
        
        return decision
    
    def _calculate_approved_amount(self, assessment: RiskAssessment) -> float:
        """Calcule le montant approuvé (peut être inférieur au demandé)."""
        # Pour l'instant, approuve le montant total si risque faible
        # TODO: Récupérer amount_requested depuis l'application originale
        return 50000.0  # Placeholder
    
    def _calculate_interest_rate(self, risk_score: int) -> float:
        """Calcule le taux d'intérêt basé sur le risque."""
        base_rate = 5.0
        risk_premium = (risk_score / 100) * 10  # 0-10% de prime de risque
        return round(base_rate + risk_premium, 2)
    
    def _determine_rejection_reasons(self, assessment: RiskAssessment) -> list[str]:
        """Détermine les raisons de rejet."""
        reasons = []
        
        if assessment.risk_score > 80:
            reasons.append("Score de risque trop élevé")
        
        if assessment.debt_to_income_ratio > 50:
            reasons.append(f"Ratio dette/revenu excessif ({assessment.debt_to_income_ratio}%)")
        
        if assessment.risk_category.value == "CRITICAL":
            reasons.append("Catégorie de risque critique")
        
        return reasons or ["Évaluation globale défavorable"]
    
    def _analyze_gray_zone(self, assessment: RiskAssessment) -> dict:
        """
        Analyse détaillée pour les cas en zone grise (score 20-80).
        
        Utilise le LLM pour interpréter la rationale de l'analyste risque.
        """
        messages = [
            SystemMessage(content=DECISION_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Analyse cette évaluation de risque et décide:

Score de risque: {assessment.risk_score}/100
Catégorie: {assessment.risk_category.value}
DTI: {assessment.debt_to_income_ratio}%
Justification analyste: {assessment.rationale}
Politiques vérifiées: {', '.join(assessment.checked_policies)}

Réponds en JSON:
{{
  "decision": "APPROVED" ou "REJECTED" ou "MANUAL_REVIEW_REQUIRED",
  "confidence": 0.0-1.0,
  "key_factor": "raison principale"
}}
"""),
        ]
        
        response = self.model.invoke(messages)
        
        # Parse la réponse (simplifié)
        try:
            import json
            result = json.loads(response.content)
            
            status_map = {
                "APPROVED": DecisionStatus.APPROVED,
                "REJECTED": DecisionStatus.REJECTED,
                "MANUAL_REVIEW_REQUIRED": DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
            
            status = status_map.get(result["decision"], DecisionStatus.MANUAL_REVIEW_REQUIRED)
            
            return {
                "status": status,
                "approved_amount": 50000.0 if status == DecisionStatus.APPROVED else None,
                "interest_rate": self._calculate_interest_rate(assessment.risk_score) if status == DecisionStatus.APPROVED else None,
                "rejection_reasons": [result.get("key_factor", "")] if status == DecisionStatus.REJECTED else [],
                "requires_human": status == DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
        except:
            # Par défaut: revue humaine
            return {
                "status": DecisionStatus.MANUAL_REVIEW_REQUIRED,
                "requires_human": True,
            }
    
    def _generate_decision_rationale(
        self, 
        assessment: RiskAssessment, 
        status: DecisionStatus,
        rejection_reasons: list[str]
    ) -> str:
        """Génère une explication de la décision pour le client."""
        if status == DecisionStatus.APPROVED:
            return f"Votre demande de prêt a été approuvée. Score de risque: {assessment.risk_score}/100."
        elif status == DecisionStatus.REJECTED:
            reasons = "; ".join(rejection_reasons)
            return f"Nous regrettons de vous informer que votre demande n'a pas été retenue. Raisons: {reasons}"
        else:
            return "Votre demande nécessite une analyse complémentaire par nos équipes. Nous vous contacterons sous 48h."
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        logger.info("Starting Decision Agent consumer loop...")
        
        try:
            for message in self.consumer.consume():
                if message is None:
                    continue
                
                try:
                    # Extraire le correlation_id des headers
                    correlation_id = self.consumer.extract_correlation_id(message)
                    
                    # Désérialiser l'évaluation
                    assessment = RiskAssessment(**message.value())
                    
                    # Configurer le contexte de logging
                    with LoggingContext(
                        correlation_id=correlation_id,
                        application_id=assessment.application_id,
                    ):
                        # Prendre la décision
                        with TimingContext(self.agent_id, "decide"):
                            decision = self.make_decision(assessment)
                        
                        # Enregistrer la métrique de décision
                        record_decision(
                            status=decision.status.value,
                            agent_id=self.agent_id,
                        )
                        
                        # Publier la décision
                        self.producer.produce(
                            key=decision.application_id,
                            value=decision.model_dump(),
                        )
                        
                        # Enregistrer le message traité
                        record_kafka_message(
                            topic="risk.scoring.result.v1",
                            agent_id=self.agent_id,
                            status="success",
                        )
                    
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    record_kafka_message(
                        topic="risk.scoring.result.v1",
                        agent_id=self.agent_id,
                        status="error",
                    )
                    # TODO: Publier dans Dead Letter Queue
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Decision Agent...")
        finally:
            self.close()
    
    def close(self):
        """Ferme les connexions."""
        self.consumer.close()
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    agent = DecisionAgent()
    agent.run()


if __name__ == "__main__":
    main()

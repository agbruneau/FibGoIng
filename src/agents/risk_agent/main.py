#!/usr/bin/env python3
"""
Risk Agent - Agent d'Analyse de Risque de Crédit
=================================================

Agent intelligent d'évaluation du risque de crédit utilisant le pattern ReAct
(Reason + Act) avec augmentation par RAG sur les politiques de crédit.

L'agent consomme des demandes de prêt depuis Kafka, effectue une analyse
multi-factorielle (DTI, historique crédit, politiques), et publie une
évaluation de risque structurée.

Architecture:
    Ce module implémente l'Agent 2 (Risk Analyst) du pipeline AgentMeshKafka.
    Il s'inscrit dans une architecture événementielle avec découplage via Kafka::

        [Intake Agent] → Kafka → [Risk Agent] → Kafka → [Decision Agent]

Pattern ReAct:
    L'agent suit le pattern ReAct pour une prise de décision explicable:
    
    1. **Thought**: Analyse du profil demandeur
    2. **Action**: Appel aux outils (RAG, calcul DTI, historique)
    3. **Observation**: Collecte des résultats
    4. **Final Answer**: Score de risque avec justification

Configuration:
    L'agent peut être configuré via variables d'environnement ou ``config.yaml``::

        # Variables d'environnement
        RISK_AGENT_MODEL=claude-sonnet-4-20250514
        RISK_AGENT_TEMPERATURE=0.2
        RISK_CONSUMER_GROUP=agent-risk-analyst
        ANTHROPIC_API_KEY=sk-ant-...

        # Équivalent config.yaml
        agents:
          risk_agent:
            model: "claude-sonnet-4-20250514"
            temperature: 0.2
            consumer_group: "agent-risk-analyst"

Usage:
    En ligne de commande::

        $ python -m src.agents.risk_agent.main

    Programmatiquement::

        from src.agents.risk_agent.main import RiskAgent
        from src.shared.models import LoanApplication, EmploymentStatus

        agent = RiskAgent()
        
        application = LoanApplication(
            application_id="APP-001",
            applicant_id="CUST-12345",
            amount_requested=50000.0,
            declared_monthly_income=5000.0,
            employment_status=EmploymentStatus.FULL_TIME,
            existing_debts=500.0,
            timestamp=1704067200000,
            currency="USD",
        )
        
        assessment = agent.analyze_application(application)
        print(f"Risk Score: {assessment.risk_score}/100")
        print(f"Category: {assessment.risk_category.value}")

Topics Kafka:
    - **Consomme**: ``finance.loan.application.v1``
    - **Produit**: ``risk.scoring.result.v1``

See Also:
    - :mod:`src.agents.decision_agent.main`: Agent de décision en aval
    - :mod:`src.shared.models`: Modèles de données Pydantic
    - ``docs/03-AgentSpecs.md``: Spécifications détaillées des agents

Note:
    Le RAG sur ChromaDB est disponible à partir de la Phase 2.
    En Phase 1, les politiques retournées sont simulées.
"""

import os
import time
import uuid
from datetime import datetime

import structlog
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import LoanApplication, RiskAssessment, RiskLevel
from src.shared.prompts import RISK_AGENT_SYSTEM_PROMPT
from src.shared.logging_config import (
    configure_logging,
    get_logger,
    set_correlation_id,
    set_application_id,
    LoggingContext,
)
from src.shared.metrics import (
    start_metrics_server,
    record_risk_score,
    record_kafka_message,
    record_processing_time,
    set_agent_info,
    TimingContext,
)

load_dotenv()

# Configurer le logging structuré
configure_logging(agent_id="agent-risk-analyst")
logger = get_logger()


class RiskAgent:
    """
    Agent d'analyse de risque de crédit avec pattern ReAct.

    Cet agent évalue le risque associé à une demande de prêt en combinant:
    
    - **RAG (Retrieval-Augmented Generation)**: Recherche sémantique dans la
      base de politiques de crédit (ChromaDB)
    - **Calculs déterministes**: Ratio dette/revenu (DTI), scoring pondéré
    - **Raisonnement LLM**: Génération de justifications en langage naturel

    L'agent consomme les messages du topic Kafka ``finance.loan.application.v1``
    et publie les évaluations dans ``risk.scoring.result.v1``.

    Attributes:
        model (ChatAnthropic): Client LLM Anthropic Claude pour le raisonnement.
        consumer (KafkaConsumerClient): Consommateur Kafka pour les demandes.
        producer (KafkaProducerClient): Producteur Kafka pour les évaluations.
        agent_id (str): Identifiant unique de l'agent pour le tracing.

    Example:
        Utilisation basique::

            agent = RiskAgent()
            agent.run()  # Démarre la boucle de consommation Kafka

        Analyse d'une demande spécifique::

            agent = RiskAgent()
            assessment = agent.analyze_application(application)
            
            if assessment.risk_score > 80:
                print("Risque critique détecté!")

    Configuration:
        +---------------------------+----------------------------------+-------------------+
        | Variable Environnement    | Description                      | Défaut            |
        +===========================+==================================+===================+
        | RISK_AGENT_MODEL          | Modèle Claude à utiliser         | claude-sonnet-4   |
        +---------------------------+----------------------------------+-------------------+
        | RISK_AGENT_TEMPERATURE    | Température du modèle (0.0-1.0)  | 0.2               |
        +---------------------------+----------------------------------+-------------------+
        | RISK_CONSUMER_GROUP       | Groupe de consommateurs Kafka    | agent-risk-analyst|
        +---------------------------+----------------------------------+-------------------+
        | ANTHROPIC_API_KEY         | Clé API Anthropic (requis)       | -                 |
        +---------------------------+----------------------------------+-------------------+

    See Also:
        - :class:`src.shared.models.RiskAssessment`: Structure de sortie
        - :class:`src.shared.models.LoanApplication`: Structure d'entrée
    """
    
    def __init__(self):
        """Initialise le RiskAgent avec LLM, Kafka, et observabilité."""
        self.model = ChatAnthropic(
            model=os.getenv("RISK_AGENT_MODEL", "claude-sonnet-4-20250514"),
            temperature=float(os.getenv("RISK_AGENT_TEMPERATURE", "0.2")),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        
        self.consumer = KafkaConsumerClient(
            topic="finance.loan.application.v1",
            group_id=os.getenv("RISK_CONSUMER_GROUP", "agent-risk-analyst"),
        )
        
        self.producer = KafkaProducerClient(
            topic="risk.scoring.result.v1",
            schema_subject="risk.scoring.result.v1-value",
        )
        
        self.agent_id = "agent-risk-analyst"
        
        # Démarrer le serveur de métriques Prometheus
        metrics_port = int(os.getenv("METRICS_PORT", "9091"))
        start_metrics_server(port=metrics_port)
        
        # Enregistrer les infos de l'agent
        set_agent_info(
            agent_id=self.agent_id,
            version="1.0.0",
            model=os.getenv("RISK_AGENT_MODEL", "claude-sonnet-4-20250514"),
        )
        
        logger.info("RiskAgent initialized", agent_id=self.agent_id)
    
    # -------------------------------------------------------------------------
    # Outils (Tools) - Voir docs/03-AgentSpecs.md Section 3.2
    # -------------------------------------------------------------------------
    
    def tool_search_credit_policy(self, query: str) -> str:
        """
        Recherche sémantique dans la base vectorielle ChromaDB.
        Contient les manuels de politique de crédit.
        
        Args:
            query: Requête de recherche
            
        Returns:
            Documents pertinents trouvés
        """
        # TODO: Implémenter la connexion ChromaDB
        # Placeholder pour le squelette
        logger.info("Searching credit policy", query=query)
        return """
        Politique 4.2 - Travailleurs Indépendants:
        - Le ratio d'endettement (DTI) ne doit pas dépasser 40%
        - Un historique de revenus de 2 ans minimum est requis
        - Le score de risque doit être > 80 si DTI > 45%
        """
    
    def tool_calculate_debt_ratio(
        self, 
        income: float, 
        existing_debts: float, 
        new_loan_amount: float
    ) -> float:
        """
        Calcule le ratio dette/revenu (DTI).
        
        Args:
            income: Revenu mensuel
            existing_debts: Dettes existantes
            new_loan_amount: Montant du nouveau prêt
            
        Returns:
            Ratio DTI en pourcentage
        """
        if income <= 0:
            return 100.0  # Risque maximum si pas de revenu
        
        # Estimation mensualité du nouveau prêt (simplifié: 1% du montant)
        estimated_monthly_payment = new_loan_amount * 0.01
        total_monthly_debt = existing_debts + estimated_monthly_payment
        
        dti = (total_monthly_debt / income) * 100
        logger.info("DTI calculated", dti=dti, income=income, debts=total_monthly_debt)
        return round(dti, 2)
    
    def tool_fetch_credit_history(self, applicant_id: str) -> dict:
        """
        Récupère l'historique de crédit externe (simulé).
        
        Args:
            applicant_id: ID du demandeur
            
        Returns:
            Historique de crédit simulé
        """
        # TODO: Connecter à un service externe
        logger.info("Fetching credit history", applicant_id=applicant_id)
        return {
            "credit_score": 720,
            "accounts_in_good_standing": 5,
            "late_payments_last_year": 0,
            "bankruptcies": 0,
        }
    
    # -------------------------------------------------------------------------
    # Logique principale
    # -------------------------------------------------------------------------
    
    def analyze_application(self, application: LoanApplication) -> RiskAssessment:
        """
        Analyse une demande de prêt et génère une évaluation de risque.
        
        Implémente le pattern ReAct:
        1. Thought: Analyse de la situation
        2. Action: Appel aux outils
        3. Observation: Résultats des outils
        4. Final Answer: Score et justification
        """
        start_time = time.time()
        chain_of_thought = []
        
        logger.info(
            "Analyzing application",
            application_id=application.application_id,
        )
        
        # Step 1: Identifier le profil et rechercher les politiques
        chain_of_thought.append(f"[THOUGHT] Demande de {application.amount_requested} USD par un {application.employment_status.value}")
        
        policy_query = f"règles {application.employment_status.value.lower()} ratio endettement"
        policies = self.tool_search_credit_policy(policy_query)
        chain_of_thought.append(f"[ACTION] search_credit_policy({policy_query})")
        chain_of_thought.append(f"[OBSERVATION] {policies[:200]}...")
        
        # Step 2: Calculer le DTI
        dti = self.tool_calculate_debt_ratio(
            income=application.declared_monthly_income,
            existing_debts=application.existing_debts,
            new_loan_amount=application.amount_requested,
        )
        chain_of_thought.append(f"[ACTION] calculate_debt_ratio(...)")
        chain_of_thought.append(f"[OBSERVATION] DTI = {dti}%")
        
        # Step 3: Récupérer l'historique de crédit
        credit_history = self.tool_fetch_credit_history(application.applicant_id)
        chain_of_thought.append(f"[ACTION] fetch_credit_history({application.applicant_id})")
        chain_of_thought.append(f"[OBSERVATION] Credit Score = {credit_history['credit_score']}")
        
        # Step 4: Déterminer le score de risque
        risk_score = self._calculate_risk_score(application, dti, credit_history)
        risk_category = self._categorize_risk(risk_score)
        
        # Step 5: Générer la justification via LLM
        rationale = self._generate_rationale(application, dti, risk_score, policies)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        assessment = RiskAssessment(
            application_id=application.application_id,
            assessment_id=str(uuid.uuid4()),
            timestamp=int(datetime.now().timestamp() * 1000),
            risk_score=risk_score,
            risk_category=risk_category,
            debt_to_income_ratio=dti,
            rationale=rationale,
            checked_policies=["Policy-4.2-SelfEmployed", "Policy-2.1-DTI-Limits"],
            confidence_score=0.85,
            chain_of_thought="\n".join(chain_of_thought),
            processing_time_ms=processing_time,
            model_used=os.getenv("RISK_AGENT_MODEL", "claude-opus-4.5"),
        )
        
        # Enregistrer les métriques
        record_risk_score(risk_score, self.agent_id)
        record_processing_time(
            duration_seconds=processing_time / 1000.0,
            agent_id=self.agent_id,
            operation="analyze",
        )
        
        logger.info(
            "Risk assessment completed",
            application_id=application.application_id,
            risk_score=risk_score,
            risk_category=risk_category.value,
            processing_time_ms=processing_time,
        )
        
        return assessment
    
    def _calculate_risk_score(
        self, 
        application: LoanApplication, 
        dti: float,
        credit_history: dict
    ) -> int:
        """Calcule le score de risque basé sur les règles métier."""
        score = 50  # Score de base
        
        # Ajustement basé sur le DTI
        if dti > 50:
            score += 40
        elif dti > 40:
            score += 25
        elif dti > 30:
            score += 10
        else:
            score -= 10
        
        # Ajustement basé sur le statut d'emploi
        if application.employment_status.value == "UNEMPLOYED":
            score += 30
        elif application.employment_status.value == "SELF_EMPLOYED":
            score += 15
        elif application.employment_status.value == "PART_TIME":
            score += 10
        
        # Ajustement basé sur l'historique de crédit
        if credit_history["credit_score"] >= 750:
            score -= 20
        elif credit_history["credit_score"] >= 700:
            score -= 10
        elif credit_history["credit_score"] < 600:
            score += 20
        
        # Limiter entre 0 et 100
        return max(0, min(100, score))
    
    def _categorize_risk(self, score: int) -> RiskLevel:
        """Catégorise le score de risque."""
        if score < 20:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_rationale(
        self, 
        application: LoanApplication, 
        dti: float, 
        risk_score: int,
        policies: str
    ) -> str:
        """Génère une justification en langage naturel via LLM."""
        messages = [
            SystemMessage(content=RISK_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Génère une justification concise (2-3 phrases) pour cette évaluation:
- Montant: {application.amount_requested} USD
- Statut emploi: {application.employment_status.value}
- DTI calculé: {dti}%
- Score de risque: {risk_score}/100
- Politiques consultées: {policies[:300]}

Cite les politiques utilisées.
"""),
        ]
        
        response = self.model.invoke(messages)
        return response.content
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        logger.info("Starting Risk Agent consumer loop...")
        
        try:
            for message in self.consumer.consume():
                if message is None:
                    continue
                
                try:
                    # Extraire le correlation_id des headers
                    correlation_id = self.consumer.extract_correlation_id(message)
                    
                    # Désérialiser l'application
                    application = LoanApplication(**message.value())
                    
                    # Configurer le contexte de logging
                    with LoggingContext(
                        correlation_id=correlation_id,
                        application_id=application.application_id,
                    ):
                        # Analyser et scorer
                        with TimingContext(self.agent_id, "analyze"):
                            assessment = self.analyze_application(application)
                        
                        # Publier le résultat
                        self.producer.produce(
                            key=assessment.application_id,
                            value=assessment.model_dump(),
                        )
                        
                        # Enregistrer le message traité
                        record_kafka_message(
                            topic="finance.loan.application.v1",
                            agent_id=self.agent_id,
                            status="success",
                        )
                    
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    record_kafka_message(
                        topic="finance.loan.application.v1",
                        agent_id=self.agent_id,
                        status="error",
                    )
                    # TODO: Publier dans Dead Letter Queue
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Risk Agent...")
        finally:
            self.close()
    
    def close(self):
        """Ferme les connexions."""
        self.consumer.close()
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    agent = RiskAgent()
    agent.run()


if __name__ == "__main__":
    main()

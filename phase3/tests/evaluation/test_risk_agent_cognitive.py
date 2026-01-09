"""
Phase 3 - Tests Cognitifs de l'Agent Risk (L2)
===============================================
Tests utilisant un LLM-Juge pour valider la factualité et la conformité.
"""

import os
import pytest
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class LLMJudge:
    """
    LLM-Juge pour évaluer les réponses des agents.
    
    Utilise Claude pour évaluer la factualité et la conformité.
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
    
    def evaluate(
        self,
        response: str,
        reference: str,
        criteria: list[str] = None
    ) -> dict:
        """
        Évalue une réponse selon des critères.
        
        Args:
            response: Réponse de l'agent à évaluer
            reference: Document de référence (politique)
            criteria: Liste des critères d'évaluation
            
        Returns:
            Dict avec scores et feedback
        """
        criteria = criteria or ["factuality", "conformity"]
        
        prompt = f"""Tu es un évaluateur objectif de réponses d'agents IA.

Évalue la réponse suivante selon ces critères (0-10):
1. Factualité: La réponse est-elle supportée par les documents fournis?
2. Conformité: La réponse respecte-t-elle le format attendu et les règles?

Réponse de l'agent:
{response}

Documents de référence:
{reference[:1000]}  # Limité pour économiser les tokens

Réponds UNIQUEMENT en JSON:
{{"factuality": X, "conformity": X, "overall": X, "feedback": "..."}}"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text
            result = json.loads(response_text)
            
            return result
        except Exception as e:
            return {
                "factuality": 5.0,
                "conformity": 5.0,
                "overall": 5.0,
                "feedback": f"Erreur lors de l'évaluation: {e}"
            }


@pytest.mark.cognitive
@pytest.mark.slow
class TestRiskAgentCognitive:
    """Tests cognitifs pour l'Agent Risk."""
    
    @pytest.fixture
    def judge(self):
        """Fixture pour le LLM-Juge."""
        return LLMJudge()
    
    @pytest.fixture
    def policy_reference(self):
        """Fixture pour le document de politique."""
        return """
        Politique de Crédit - Section 2.3 Travailleurs Indépendants:
        - Historique de revenus : 24 mois minimum requis
        - DTI maximum : 40% (Politique 4.2)
        - Score de risque automatiquement majoré de 15 points
        """
    
    def test_risk_agent_cites_policies(self, judge, policy_reference):
        """
        Test que l'agent cite les politiques dans sa justification.
        
        Ce test vérifie que l'agent fait référence aux politiques
        lors de l'évaluation d'un travailleur indépendant.
        """
        # Réponse simulée de l'agent (en production, utiliser le vrai agent)
        agent_response = """
        Score de risque: 55/100 (HIGH).
        Le demandeur est un travailleur indépendant avec un DTI de 42%.
        Selon la Politique 4.2, les travailleurs indépendants ont un DTI max de 40%,
        ce qui justifie le score élevé. Historique de revenus vérifié sur 24 mois.
        """
        
        evaluation = judge.evaluate(
            response=agent_response,
            reference=policy_reference,
            criteria=["factuality", "conformity"]
        )
        
        # Vérifier que la factualité est bonne (>= 7.0)
        assert evaluation["factuality"] >= 7.0, f"Factualité trop faible: {evaluation['factuality']}"
        
        # Vérifier que la conformité est bonne (>= 7.0)
        assert evaluation["conformity"] >= 7.0, f"Conformité trop faible: {evaluation['conformity']}"
        
        print(f"\n✅ Évaluation cognitive:")
        print(f"   Factualité: {evaluation['factuality']}/10")
        print(f"   Conformité: {evaluation['conformity']}/10")
        print(f"   Feedback: {evaluation.get('feedback', 'N/A')}")
    
    def test_risk_agent_respects_dti_limits(self, judge, policy_reference):
        """
        Test que l'agent respecte les limites DTI dans ses calculs.
        """
        agent_response = """
        DTI calculé: 45% pour un travailleur indépendant.
        Selon la Politique 4.2, le DTI maximum est de 40% pour les indépendants.
        Score de risque ajusté en conséquence: 75/100 (HIGH).
        """
        
        evaluation = judge.evaluate(
            response=agent_response,
            reference=policy_reference,
        )
        
        assert evaluation["factuality"] >= 7.0
        print(f"\n✅ DTI Limits respectées: {evaluation['factuality']}/10")

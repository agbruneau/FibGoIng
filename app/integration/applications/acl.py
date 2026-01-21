"""Anti-Corruption Layer - Adaptation des systemes legacy."""
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass


class ProductType(Enum):
    """Types de produits d'assurance."""
    AUTO = "AUTO"
    HABITATION = "HABITATION"
    MRH = "MRH"
    OTHER = "OTHER"


class PolicyStatus(Enum):
    """Statuts possibles d'une police."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


@dataclass
class Policy:
    """Modele de police dans notre domaine."""
    number: str
    product: ProductType
    customer_id: str
    premium: Decimal
    status: PolicyStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class LegacyPASAdapter:
    """
    Anti-Corruption Layer pour le Policy Admin System legacy.

    Traduit entre le format SOAP/XML legacy et notre modele moderne.
    """

    # Mappings legacy -> moderne
    PRODUCT_MAPPING = {
        "AUTMRP": ProductType.AUTO,
        "AUTECO": ProductType.AUTO,
        "HABMRH": ProductType.HABITATION,
        "MRHSTD": ProductType.MRH,
        "MRHPRE": ProductType.MRH,
    }

    STATUS_MAPPING = {
        "ACT": PolicyStatus.ACTIVE,
        "SUS": PolicyStatus.SUSPENDED,
        "RES": PolicyStatus.CANCELLED,
        "ANN": PolicyStatus.CANCELLED,
        "EXP": PolicyStatus.EXPIRED,
        "BRO": PolicyStatus.DRAFT,
    }

    # Mappings inverse moderne -> legacy
    PRODUCT_REVERSE = {v: k for k, v in PRODUCT_MAPPING.items()}
    STATUS_REVERSE = {v: k for k, v in STATUS_MAPPING.items()}

    def __init__(self, legacy_client=None):
        """
        Args:
            legacy_client: Client SOAP/HTTP pour le systeme legacy (optionnel)
        """
        self.client = legacy_client

    def translate_to_modern(self, legacy_data: dict) -> Policy:
        """
        Traduit une reponse legacy vers notre modele moderne.

        Args:
            legacy_data: Donnees au format legacy

        Returns:
            Objet Policy dans notre domaine
        """
        # Traduction du numero de police
        policy_number = self._translate_policy_number(legacy_data.get("NumContrat", ""))

        # Traduction du produit
        legacy_product = legacy_data.get("CodeProduit", "")
        product = self.PRODUCT_MAPPING.get(legacy_product, ProductType.OTHER)

        # Traduction du client
        customer_id = self._translate_customer_id(legacy_data.get("NumClient", ""))

        # Traduction du montant (legacy en centimes)
        legacy_amount = legacy_data.get("MontPrime", 0)
        premium = Decimal(legacy_amount) / 100

        # Traduction du statut
        legacy_status = legacy_data.get("StatutCtr", "")
        status = self.STATUS_MAPPING.get(legacy_status, PolicyStatus.UNKNOWN)

        # Traduction des dates (format legacy: YYYYMMDD)
        start_date = self._parse_legacy_date(legacy_data.get("DtDebEff"))
        end_date = self._parse_legacy_date(legacy_data.get("DtFinEff"))

        return Policy(
            number=policy_number,
            product=product,
            customer_id=customer_id,
            premium=premium,
            status=status,
            start_date=start_date,
            end_date=end_date
        )

    def translate_to_legacy(self, policy: Policy) -> dict:
        """
        Traduit notre modele vers le format legacy.

        Args:
            policy: Objet Policy de notre domaine

        Returns:
            Dictionnaire au format legacy
        """
        # Traduction inverse du produit
        legacy_product = self.PRODUCT_REVERSE.get(policy.product, "AUTRE")

        # Traduction inverse du numero client
        legacy_customer = policy.customer_id.replace("C", "").lstrip("0")

        # Traduction du montant (vers centimes)
        legacy_amount = int(policy.premium * 100)

        # Traduction inverse du statut
        legacy_status = self.STATUS_REVERSE.get(policy.status, "ACT")

        # Traduction des dates
        legacy_start = self._format_legacy_date(policy.start_date)
        legacy_end = self._format_legacy_date(policy.end_date)

        return {
            "NumContrat": policy.number.replace("POL-", ""),
            "CodeProduit": legacy_product,
            "NumClient": legacy_customer,
            "MontPrime": legacy_amount,
            "StatutCtr": legacy_status,
            "DtDebEff": legacy_start,
            "DtFinEff": legacy_end
        }

    def translate_to_dict(self, policy: Policy) -> dict:
        """Convertit un objet Policy en dictionnaire."""
        return {
            "number": policy.number,
            "product": policy.product.value,
            "customer_id": policy.customer_id,
            "premium": float(policy.premium),
            "status": policy.status.value,
            "start_date": policy.start_date.isoformat() if policy.start_date else None,
            "end_date": policy.end_date.isoformat() if policy.end_date else None
        }

    # Methodes de traduction specifiques

    def _translate_policy_number(self, legacy_number: str) -> str:
        """Traduit un numero de police legacy vers le format moderne."""
        if not legacy_number:
            return ""
        # Legacy: "12345678" -> Moderne: "POL-12345678"
        return f"POL-{legacy_number}"

    def _translate_customer_id(self, legacy_id: str) -> str:
        """Traduit un ID client legacy vers le format moderne."""
        if not legacy_id:
            return ""
        # Legacy: "987654" -> Moderne: "C987654"
        return f"C{legacy_id.zfill(6)}"

    def _parse_legacy_date(self, date_str: str) -> Optional[datetime]:
        """Parse une date au format legacy YYYYMMDD."""
        if not date_str or len(date_str) != 8:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            return None

    def _format_legacy_date(self, dt: Optional[datetime]) -> str:
        """Formate une date vers le format legacy."""
        if not dt:
            return ""
        return dt.strftime("%Y%m%d")


class LegacyRatingAdapter:
    """
    ACL pour le service de notation externe legacy.

    Traduit le format de score externe vers notre modele.
    """

    SCORE_MAPPING = {
        "A+": 10,
        "A": 20,
        "A-": 30,
        "B+": 40,
        "B": 50,
        "B-": 60,
        "C+": 70,
        "C": 80,
        "C-": 90,
        "D": 100
    }

    RISK_LEVEL_MAPPING = {
        "VERY_LOW": "LOW_RISK",
        "LOW": "LOW_RISK",
        "MEDIUM": "MEDIUM_RISK",
        "HIGH": "HIGH_RISK",
        "VERY_HIGH": "HIGH_RISK"
    }

    def translate_risk_score(self, legacy_response: dict) -> dict:
        """
        Traduit une reponse de scoring legacy.

        Legacy format:
        {
            "score": "A+",
            "risk_level": "LOW",
            "factors": ["age:OK", "claims:WARN"]
        }

        Modern format:
        {
            "score": 10,
            "category": "LOW_RISK",
            "factors": [{"name": "age", "status": "OK"}, ...]
        }
        """
        # Traduction du score
        legacy_score = legacy_response.get("score", "C")
        modern_score = self.SCORE_MAPPING.get(legacy_score, 50)

        # Traduction du niveau de risque
        legacy_level = legacy_response.get("risk_level", "MEDIUM")
        modern_category = self.RISK_LEVEL_MAPPING.get(legacy_level, "MEDIUM_RISK")

        # Traduction des facteurs
        legacy_factors = legacy_response.get("factors", [])
        modern_factors = []

        for factor in legacy_factors:
            if ":" in factor:
                name, status = factor.split(":", 1)
                modern_factors.append({
                    "name": name.strip(),
                    "status": self._translate_factor_status(status.strip())
                })

        return {
            "score": modern_score,
            "category": modern_category,
            "factors": modern_factors,
            "original_score": legacy_score,
            "translated_at": datetime.now().isoformat()
        }

    def _translate_factor_status(self, status: str) -> str:
        """Traduit un statut de facteur."""
        mapping = {
            "OK": "normal",
            "WARN": "elevated",
            "ALERT": "critical",
            "NA": "not_applicable"
        }
        return mapping.get(status.upper(), "unknown")

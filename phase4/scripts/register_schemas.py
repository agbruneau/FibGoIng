#!/usr/bin/env python3
"""
AgentMeshKafka - Schema Registry Registration Script (Phase 4)
================================================================
Enregistre les schémas Avro dans le Confluent Schema Registry.
Voir docs/02-DataContracts.md pour les contrats de données.

Usage:
    python scripts/register_schemas.py
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

# Mapping Topic -> Schema File
SCHEMA_MAPPINGS = [
    {
        "subject": "finance.loan.application.v1-value",
        "schema_file": "loan_application.avsc",
        "description": "Demande de prêt soumise",
    },
    {
        "subject": "risk.scoring.result.v1-value",
        "schema_file": "risk_assessment.avsc",
        "description": "Évaluation de risque complétée",
    },
    {
        "subject": "finance.loan.decision.v1-value",
        "schema_file": "loan_decision.avsc",
        "description": "Décision finale de prêt",
    },
]


def load_schema(schema_path: Path) -> dict:
    """Charge un fichier schema Avro."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def register_schema(registry_url: str, subject: str, schema: dict) -> int:
    """Enregistre un schéma dans le Schema Registry."""
    url = f"{registry_url}/subjects/{subject}/versions"
    
    payload = {
        "schemaType": "AVRO",
        "schema": json.dumps(schema),
    }
    
    response = httpx.post(
        url,
        json=payload,
        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
    )
    
    if response.status_code == 200:
        return response.json()["id"]
    elif response.status_code == 409:
        # Schema déjà enregistré (identique)
        return -1
    else:
        raise Exception(f"Erreur {response.status_code}: {response.text}")


def check_compatibility(registry_url: str, subject: str, schema: dict) -> bool:
    """Vérifie la compatibilité du schéma avec la version précédente."""
    url = f"{registry_url}/compatibility/subjects/{subject}/versions/latest"
    
    payload = {
        "schemaType": "AVRO",
        "schema": json.dumps(schema),
    }
    
    response = httpx.post(
        url,
        json=payload,
        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
    )
    
    if response.status_code == 200:
        return response.json().get("is_compatible", True)
    elif response.status_code == 404:
        # Pas de version précédente
        return True
    else:
        return False


def main():
    """Point d'entrée principal."""
    registry_url = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    schemas_dir = Path(__file__).parent.parent / "schemas"
    
    print(f"🔌 Connexion au Schema Registry: {registry_url}")
    print(f"📁 Dossier des schémas: {schemas_dir}\n")
    
    # Vérifier la connexion
    try:
        response = httpx.get(f"{registry_url}/subjects", timeout=5)
        response.raise_for_status()
        existing_subjects = response.json()
        print(f"📋 Subjects existants: {len(existing_subjects)}\n")
    except Exception as e:
        print(f"❌ Impossible de se connecter au Schema Registry: {e}")
        print("   Assurez-vous que docker-compose est démarré!")
        sys.exit(1)
    
    # Enregistrer chaque schéma
    success_count = 0
    for mapping in SCHEMA_MAPPINGS:
        subject = mapping["subject"]
        schema_file = schemas_dir / mapping["schema_file"]
        
        print(f"📝 Traitement: {mapping['description']}")
        print(f"   Subject: {subject}")
        print(f"   Fichier: {schema_file.name}")
        
        if not schema_file.exists():
            print(f"   ❌ Fichier non trouvé!")
            continue
        
        schema = load_schema(schema_file)
        
        # Vérifier la compatibilité si le subject existe
        if subject in existing_subjects:
            is_compatible = check_compatibility(registry_url, subject, schema)
            if not is_compatible:
                print(f"   ⚠️  INCOMPATIBLE avec la version précédente!")
                print(f"   Voir docs/02-DataContracts.md pour la politique FORWARD")
                continue
        
        # Enregistrer le schéma
        try:
            schema_id = register_schema(registry_url, subject, schema)
            if schema_id > 0:
                print(f"   ✅ Enregistré (ID: {schema_id})")
            else:
                print(f"   ⏭️  Schéma identique déjà enregistré")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
        
        print()
    
    print(f"🎉 Terminé! {success_count}/{len(SCHEMA_MAPPINGS)} schémas traités.")


if __name__ == "__main__":
    main()

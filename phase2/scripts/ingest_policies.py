#!/usr/bin/env python3
"""
Phase 2 - Ingestion des Politiques de Crédit
=============================================
Ingère le document de politique dans ChromaDB.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.rag_client import RAGClient

def main():
    """Ingère le document de politique."""
    # Lire le fichier de politique
    policy_file = Path(__file__).parent.parent / "data" / "credit_policy.md"
    
    if not policy_file.exists():
        print(f"❌ Fichier non trouvé: {policy_file}")
        return
    
    with open(policy_file, 'r', encoding='utf-8') as f:
        policy_text = f.read()
    
    print("📚 Ingestion des politiques de crédit dans ChromaDB...")
    
    # Créer le client RAG
    rag_client = RAGClient()
    
    # Vider la collection existante (pour ré-ingestion)
    try:
        rag_client.client.delete_collection(rag_client.COLLECTION_NAME)
        rag_client.collection = rag_client.client.create_collection(
            name=rag_client.COLLECTION_NAME,
            metadata={"description": "Politiques de crédit"}
        )
        print("🗑️  Collection vidée")
    except:
        pass
    
    # Ingérer le document
    rag_client.ingest_document(
        text=policy_text,
        metadata={"source": "credit_policy.md", "version": "1.0"}
    )
    
    print("✅ Documents ingérés avec succès!")
    print(f"💡 Collection: {rag_client.COLLECTION_NAME}")
    print(f"💡 Testez avec: python -c \"from src.shared.rag_client import RAGClient; print(RAGClient().search('règles travailleurs indépendants'))\"")


if __name__ == "__main__":
    main()

"""
Phase 2 - RAG Client avec ChromaDB
===================================
Client pour la recherche sémantique dans ChromaDB.
"""

import os
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


class RAGClient:
    """
    Client RAG pour ChromaDB.
    
    Gère l'ingestion et la recherche de documents.
    """
    
    COLLECTION_NAME = "credit_policies"
    
    def __init__(self):
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        
        self.client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Modèle d'embedding (léger pour la démo)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Récupérer ou créer la collection
        try:
            self.collection = self.client.get_collection(self.COLLECTION_NAME)
            print(f"✅ Collection '{self.COLLECTION_NAME}' trouvée")
        except:
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Politiques de crédit"}
            )
            print(f"✅ Collection '{self.COLLECTION_NAME}' créée")
    
    def ingest_document(self, text: str, metadata: Optional[dict] = None):
        """
        Ingère un document dans ChromaDB.
        
        Args:
            text: Texte du document
            metadata: Métadonnées optionnelles
        """
        # Découper en chunks (simplifié: par paragraphe)
        chunks = self._chunk_text(text)
        
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                chunk_id = f"chunk_{len(ids)}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(metadata or {})
        
        # Générer les embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        # Ajouter à la collection
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        print(f"✅ {len(ids)} chunks ingérés")
    
    def search(self, query: str, n_results: int = 3) -> List[str]:
        """
        Recherche sémantique dans la collection.
        
        Args:
            query: Requête de recherche
            n_results: Nombre de résultats à retourner
            
        Returns:
            Liste de documents pertinents
        """
        # Générer l'embedding de la requête
        query_embedding = self.embedder.encode([query]).tolist()[0]
        
        # Rechercher dans ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Extraire les documents
        documents = results.get('documents', [])
        if documents and len(documents) > 0:
            return documents[0]  # Premier résultat (liste de documents)
        
        return []
    
    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """
        Découpe un texte en chunks.
        
        Args:
            text: Texte à découper
            chunk_size: Taille approximative des chunks
            
        Returns:
            Liste de chunks
        """
        # Découpage simple par paragraphe
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

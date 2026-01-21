"""Service mock pour la gestion électronique des documents."""
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
from .base import MockService


class DocumentManagement(MockService):
    """
    Simule le système GED (Gestion Électronique des Documents).

    Fonctionnalités:
    - Upload et stockage de documents
    - Métadonnées et tags
    - Liaison avec entités (polices, sinistres, clients)
    """

    VALID_TYPES = ["PDF", "IMAGE", "WORD", "EXCEL", "OTHER"]
    VALID_CATEGORIES = [
        "CONTRAT", "AVENANT", "ATTESTATION", "FACTURE",
        "DECLARATION_SINISTRE", "EXPERTISE", "JUSTIFICATIF",
        "CORRESPONDANCE", "AUTRE"
    ]

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Document Management", default_latency=60)
        self.documents: Dict[str, Dict] = {}

        # Charger les données initiales
        if initial_data:
            for doc in initial_data:
                self.documents[doc["id"]] = doc

    def _generate_document_id(self) -> str:
        """Génère un ID de document unique."""
        seq = len(self.documents) + 1
        return f"DOC-{seq:04d}"

    async def upload_document(
        self,
        filename: str,
        content_type: str,
        category: str,
        entity_type: str = None,
        entity_id: str = None,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Upload un nouveau document.

        Args:
            filename: Nom du fichier
            content_type: Type de document (PDF, IMAGE, etc.)
            category: Catégorie métier
            entity_type: Type d'entité liée (policy, claim, customer)
            entity_id: ID de l'entité liée
            metadata: Métadonnées additionnelles

        Returns:
            Document créé
        """
        async def _upload():
            content_type_upper = content_type.upper()
            category_upper = category.upper()

            if content_type_upper not in self.VALID_TYPES:
                return {"error": True, "code": "INVALID_TYPE", "message": f"Invalid type: {content_type}"}

            if category_upper not in self.VALID_CATEGORIES:
                return {"error": True, "code": "INVALID_CATEGORY", "message": f"Invalid category: {category}"}

            now = datetime.now()
            doc_id = self._generate_document_id()

            # Simuler un hash de contenu
            content_hash = hashlib.md5(f"{doc_id}{now}".encode()).hexdigest()

            document = {
                "id": doc_id,
                "filename": filename,
                "content_type": content_type_upper,
                "category": category_upper,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "metadata": metadata or {},
                "size_bytes": 1024 * (abs(hash(filename)) % 1000 + 100),
                "content_hash": content_hash,
                "storage_path": f"/documents/{now.year}/{now.month:02d}/{doc_id}",
                "status": "ACTIVE",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.documents[doc_id] = document
            return document

        return await self.execute("upload_document", _upload)

    async def get_document(self, document_id: str) -> Optional[Dict]:
        """Récupère un document par son ID."""
        async def _get():
            doc = self.documents.get(document_id)
            if not doc:
                return {"error": True, "code": "NOT_FOUND", "message": f"Document {document_id} not found"}

            if doc["status"] == "DELETED":
                return {"error": True, "code": "DELETED", "message": f"Document {document_id} has been deleted"}

            return doc

        return await self.execute("get_document", _get)

    async def list_documents(
        self,
        entity_type: str = None,
        entity_id: str = None,
        category: str = None
    ) -> List[Dict]:
        """Liste les documents avec filtres."""
        async def _list():
            result = [d for d in self.documents.values() if d["status"] == "ACTIVE"]

            if entity_type:
                result = [d for d in result if d.get("entity_type") == entity_type]

            if entity_id:
                result = [d for d in result if d.get("entity_id") == entity_id]

            if category:
                result = [d for d in result if d["category"] == category.upper()]

            return result

        return await self.execute("list_documents", _list)

    async def update_metadata(self, document_id: str, metadata: dict) -> Dict:
        """Met à jour les métadonnées d'un document."""
        async def _update():
            doc = self.documents.get(document_id)
            if not doc:
                return {"error": True, "code": "NOT_FOUND", "message": f"Document {document_id} not found"}

            if doc["status"] == "DELETED":
                return {"error": True, "code": "DELETED", "message": "Cannot update deleted document"}

            doc["metadata"].update(metadata)
            doc["updated_at"] = datetime.now().isoformat()
            return doc

        return await self.execute("update_metadata", _update)

    async def delete_document(self, document_id: str) -> Dict:
        """Supprime un document (soft delete)."""
        async def _delete():
            doc = self.documents.get(document_id)
            if not doc:
                return {"error": True, "code": "NOT_FOUND", "message": f"Document {document_id} not found"}

            doc["status"] = "DELETED"
            doc["deleted_at"] = datetime.now().isoformat()
            doc["updated_at"] = datetime.now().isoformat()
            return {"success": True, "document_id": document_id}

        return await self.execute("delete_document", _delete)

    async def link_to_entity(
        self,
        document_id: str,
        entity_type: str,
        entity_id: str
    ) -> Dict:
        """Lie un document à une entité."""
        async def _link():
            doc = self.documents.get(document_id)
            if not doc:
                return {"error": True, "code": "NOT_FOUND", "message": f"Document {document_id} not found"}

            if doc["status"] == "DELETED":
                return {"error": True, "code": "DELETED", "message": "Cannot link deleted document"}

            doc["entity_type"] = entity_type
            doc["entity_id"] = entity_id
            doc["updated_at"] = datetime.now().isoformat()
            return doc

        return await self.execute("link_to_entity", _link)

    async def get_entity_documents(self, entity_type: str, entity_id: str) -> List[Dict]:
        """Récupère tous les documents liés à une entité."""
        return await self.list_documents(entity_type=entity_type, entity_id=entity_id)

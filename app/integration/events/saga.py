"""
Saga Orchestrator pour transactions distribuées.

Implémente le pattern Saga avec compensation automatique en cas d'échec.
"""
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid


class SagaStatus(Enum):
    """Statuts possibles d'une saga."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    """Représente une étape de la saga."""
    name: str
    action: Callable
    compensate: Optional[Callable] = None
    timeout: float = 30.0
    retries: int = 3


@dataclass
class SagaExecution:
    """Trace d'exécution d'une saga."""
    saga_id: str
    status: SagaStatus
    steps_completed: List[str] = field(default_factory=list)
    steps_compensated: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "saga_id": self.saga_id,
            "status": self.status.value,
            "steps_completed": self.steps_completed,
            "steps_compensated": self.steps_compensated,
            "current_step": self.current_step,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "context": self.context
        }


class SagaOrchestrator:
    """
    Orchestrateur de Saga pour coordonner des transactions distribuées.

    Fonctionnalités:
    - Exécution séquentielle des étapes
    - Compensation automatique en cas d'échec
    - Retry avec backoff
    - Suivi de l'état
    """

    def __init__(self):
        self.steps: List[SagaStep] = []
        self._executions: Dict[str, SagaExecution] = {}
        self._event_handlers: List[Callable] = []

    def add_step(
        self,
        action: Union[str, Callable],
        compensate: Optional[Union[str, Callable]] = None,
        name: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 3
    ):
        """
        Ajoute une étape à la saga.

        Args:
            action: Fonction à exécuter ou nom de l'étape
            compensate: Fonction de compensation (rollback)
            name: Nom de l'étape (optionnel)
            timeout: Délai max en secondes
            retries: Nombre de tentatives
        """
        # Si action est un string, on crée une fonction placeholder
        if isinstance(action, str):
            step_name = action
            action_func = self._create_placeholder(action)
        else:
            step_name = name or f"step_{len(self.steps) + 1}"
            action_func = action

        # Même chose pour compensate
        if isinstance(compensate, str):
            compensate_func = self._create_placeholder(compensate)
        else:
            compensate_func = compensate

        step = SagaStep(
            name=step_name,
            action=action_func,
            compensate=compensate_func,
            timeout=timeout,
            retries=retries
        )
        self.steps.append(step)

    def _create_placeholder(self, name: str) -> Callable:
        """Crée une fonction placeholder pour un nom d'étape."""
        async def placeholder(ctx):
            return {"step": name, "status": "executed"}
        return placeholder

    async def execute(self, context: Dict[str, Any] = None) -> Dict:
        """
        Exécute la saga complète.

        Args:
            context: Contexte initial partagé entre les étapes

        Returns:
            Résultat de l'exécution avec statut
        """
        saga_id = f"SAGA-{uuid.uuid4().hex[:8].upper()}"
        ctx = context or {}
        ctx["saga_id"] = saga_id

        execution = SagaExecution(
            saga_id=saga_id,
            status=SagaStatus.RUNNING,
            context=ctx
        )
        self._executions[saga_id] = execution

        await self._notify_event("saga_started", {
            "saga_id": saga_id,
            "steps": [s.name for s in self.steps]
        })

        completed_steps: List[SagaStep] = []

        try:
            # Exécuter chaque étape
            for step in self.steps:
                execution.current_step = step.name
                await self._notify_event("step_started", {
                    "saga_id": saga_id,
                    "step": step.name
                })

                # Exécuter avec retry
                result = await self._execute_with_retry(step, ctx)

                # Mettre à jour le contexte avec le résultat
                if isinstance(result, dict):
                    ctx.update(result)

                completed_steps.append(step)
                execution.steps_completed.append(step.name)

                await self._notify_event("step_completed", {
                    "saga_id": saga_id,
                    "step": step.name,
                    "result": result
                })

            # Succès complet
            execution.status = SagaStatus.COMPLETED
            execution.completed_at = datetime.now().isoformat()
            execution.current_step = None

            await self._notify_event("saga_completed", {
                "saga_id": saga_id
            })

            return {
                "status": "COMPLETED",
                "saga_id": saga_id,
                "context": ctx
            }

        except Exception as e:
            # Échec - lancer la compensation
            execution.status = SagaStatus.FAILED
            execution.error = str(e)
            failed_step_name = execution.current_step

            await self._notify_event("saga_failed", {
                "saga_id": saga_id,
                "step": failed_step_name,
                "error": str(e)
            })

            # Compenser les étapes complétées (en ordre inverse)
            compensation_result = await self._compensate(
                saga_id,
                execution,
                completed_steps,
                ctx
            )

            return {
                "status": "COMPENSATED" if compensation_result else "COMPENSATION_FAILED",
                "saga_id": saga_id,
                "error": str(e),
                "failed_step": failed_step_name,
                "compensated_steps": execution.steps_compensated,
                "context": ctx
            }

    async def _execute_with_retry(
        self,
        step: SagaStep,
        context: Dict
    ) -> Any:
        """Exécute une étape avec retry."""
        last_error = None

        for attempt in range(step.retries):
            try:
                # Exécuter avec timeout
                if asyncio.iscoroutinefunction(step.action):
                    result = await asyncio.wait_for(
                        step.action(context),
                        timeout=step.timeout
                    )
                else:
                    result = step.action(context)

                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Step {step.name} timed out")
            except Exception as e:
                last_error = e

            # Backoff avant retry
            if attempt < step.retries - 1:
                await asyncio.sleep(0.1 * (2 ** attempt))

        raise last_error or Exception(f"Step {step.name} failed")

    async def _compensate(
        self,
        saga_id: str,
        execution: SagaExecution,
        completed_steps: List[SagaStep],
        context: Dict
    ) -> bool:
        """
        Compense les étapes complétées en ordre inverse.

        Returns:
            True si toutes les compensations ont réussi
        """
        execution.status = SagaStatus.COMPENSATING

        await self._notify_event("compensation_started", {
            "saga_id": saga_id,
            "steps_to_compensate": [s.name for s in completed_steps]
        })

        all_compensated = True

        # Compenser en ordre inverse
        for step in reversed(completed_steps):
            if step.compensate is None:
                continue

            execution.current_step = f"compensate_{step.name}"

            try:
                await self._notify_event("compensation_step_started", {
                    "saga_id": saga_id,
                    "step": step.name
                })

                if asyncio.iscoroutinefunction(step.compensate):
                    await step.compensate(context)
                else:
                    step.compensate(context)

                execution.steps_compensated.append(step.name)

                await self._notify_event("compensation_step_completed", {
                    "saga_id": saga_id,
                    "step": step.name
                })

            except Exception as e:
                all_compensated = False
                await self._notify_event("compensation_step_failed", {
                    "saga_id": saga_id,
                    "step": step.name,
                    "error": str(e)
                })

        execution.status = SagaStatus.COMPENSATED if all_compensated else SagaStatus.FAILED
        execution.completed_at = datetime.now().isoformat()
        execution.current_step = None

        await self._notify_event("compensation_completed", {
            "saga_id": saga_id,
            "all_compensated": all_compensated
        })

        return all_compensated

    def on_event(self, handler: Callable):
        """Enregistre un handler pour les événements de saga."""
        self._event_handlers.append(handler)

    async def _notify_event(self, event_type: str, data: Dict):
        """Notifie les handlers d'un événement."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass

    def get_execution(self, saga_id: str) -> Optional[SagaExecution]:
        """Retourne l'exécution d'une saga."""
        return self._executions.get(saga_id)

    def get_all_executions(self) -> List[Dict]:
        """Retourne toutes les exécutions."""
        return [e.to_dict() for e in self._executions.values()]


# ========== SAGA SOUSCRIPTION ASSURANCE ==========

class SubscriptionSaga(SagaOrchestrator):
    """
    Saga pour le processus de souscription d'assurance.

    Étapes:
    1. Valider le devis
    2. Créer la police
    3. Créer la facture
    4. Générer les documents
    5. Envoyer les notifications
    """

    def __init__(self, services: Dict = None):
        super().__init__()
        self.services = services or {}

        # Définir les étapes
        self.add_step(
            action=self._validate_quote,
            compensate=None,  # Pas de compensation pour validation
            name="validate_quote"
        )
        self.add_step(
            action=self._create_policy,
            compensate=self._cancel_policy,
            name="create_policy"
        )
        self.add_step(
            action=self._create_invoice,
            compensate=self._cancel_invoice,
            name="create_invoice"
        )
        self.add_step(
            action=self._generate_documents,
            compensate=self._delete_documents,
            name="generate_documents"
        )
        self.add_step(
            action=self._send_notifications,
            compensate=None,  # Pas de rollback pour notifs
            name="send_notifications"
        )

    async def _validate_quote(self, ctx):
        """Valide le devis."""
        quote_id = ctx.get("quote_id")
        # Simulation
        await asyncio.sleep(0.05)
        return {"quote_validated": True, "quote_id": quote_id}

    async def _create_policy(self, ctx):
        """Crée la police."""
        await asyncio.sleep(0.05)
        policy_id = f"POL-{uuid.uuid4().hex[:8].upper()}"
        ctx["policy_id"] = policy_id
        return {"policy_id": policy_id}

    async def _cancel_policy(self, ctx):
        """Annule la police (compensation)."""
        await asyncio.sleep(0.02)
        policy_id = ctx.get("policy_id")
        return {"cancelled_policy": policy_id}

    async def _create_invoice(self, ctx):
        """Crée la facture."""
        await asyncio.sleep(0.05)
        invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        ctx["invoice_id"] = invoice_id
        return {"invoice_id": invoice_id}

    async def _cancel_invoice(self, ctx):
        """Annule la facture (compensation)."""
        await asyncio.sleep(0.02)
        invoice_id = ctx.get("invoice_id")
        return {"cancelled_invoice": invoice_id}

    async def _generate_documents(self, ctx):
        """Génère les documents."""
        await asyncio.sleep(0.05)
        doc_ids = [f"DOC-{uuid.uuid4().hex[:6].upper()}" for _ in range(3)]
        ctx["document_ids"] = doc_ids
        return {"document_ids": doc_ids}

    async def _delete_documents(self, ctx):
        """Supprime les documents (compensation)."""
        await asyncio.sleep(0.02)
        return {"deleted_documents": ctx.get("document_ids", [])}

    async def _send_notifications(self, ctx):
        """Envoie les notifications."""
        await asyncio.sleep(0.02)
        return {"notifications_sent": True}

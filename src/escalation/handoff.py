"""Human-in-the-loop handoff mechanism."""

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..surfaces.base import Surface
from ..observability.logger import StructuredLogger


@dataclass
class EscalationRequest:
    """Request for human intervention."""

    artifact_id: str
    step_id: int
    reason: str
    context: Dict[str, Any]
    screenshot_path: Optional[str] = None


@dataclass
class EscalationResult:
    """Result of human intervention."""

    resumed: bool
    actions_taken: list
    notes: str


class HandoffManager:
    """Manage control transfer to human operators."""

    def __init__(self, surface: Surface, logger: StructuredLogger):
        self.surface = surface
        self.logger = logger
        self._control_state = "automation"  # "automation" | "human"
        self._escalation_queue = asyncio.Queue()

    async def escalate(
        self, artifact_id: str, step_id: int, reason: str, context: Dict[str, Any]
    ) -> EscalationResult:
        """
        Escalate to human operator.

        Flow:
        1. Pause automation
        2. Capture current state
        3. Route to operator (mock in this implementation)
        4. Wait for human to complete
        5. Resume automation
        """
        self.logger.info(
            "escalation_started",
            artifact_id=artifact_id,
            step_id=step_id,
            reason=reason,
        )

        # Pause automation
        self._control_state = "human"

        # Capture state
        state = await self.surface.get_state()
        screenshot_path = f"evidence/escalation_{artifact_id}_{step_id}.png"
        await self.surface.screenshot(screenshot_path)

        # Create escalation request
        request = EscalationRequest(
            artifact_id=artifact_id,
            step_id=step_id,
            reason=reason,
            context=context,
            screenshot_path=screenshot_path,
        )

        # Route to operator (in production, this would be WebSocket/queue)
        # For this implementation, we'll simulate operator action
        result = await self._simulate_operator_intervention(request)

        # Resume automation
        self._control_state = "automation"

        self.logger.info(
            "escalation_completed", artifact_id=artifact_id, resumed=result.resumed
        )

        return result

    async def _simulate_operator_intervention(
        self, request: EscalationRequest
    ) -> EscalationResult:
        """
        Simulate human operator intervention.

        In production, this would:
        1. Send request to operator console via WebSocket
        2. Expose live session (CDP/VNC/screen sharing)
        3. Wait for operator to signal completion
        4. Capture actions taken
        """
        from dataclasses import asdict

        # Mock: Simulate operator reviewing and resuming
        self.logger.info("operator_notified", request=request)
        # Simulate operator review time
        await asyncio.sleep(2)
        # In real implementation:
        # - Operator sees live session
        # - Can take control and perform manual steps
        # - Signals when ready to hand back

        # For demo, we'll just log and resume
        return EscalationResult(
            resumed=True,
            actions_taken=["operator_reviewed", "manual_navigation"],
            notes="Operator manually navigated past stuck state",
        )

    def get_control_state(self) -> str:
        """Get current control state."""
        return self._control_state

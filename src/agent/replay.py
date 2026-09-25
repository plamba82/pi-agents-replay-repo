"""Deterministic replay engine - production execution path."""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from ..models.artifact import CapabilityArtifact, ActionType, LocatorStrategy
from ..models.execution import ExecutionResult, ExecutionStatus, ExecutionStep
from ..surfaces.base import Surface
from ..safety.guardrails import GuardrailEngine
from ..observability.logger import StructuredLogger
from ..observability.evidence import EvidenceCollector
from ..escalation.detector import StuckDetector
from ..escalation.handoff import HandoffManager


class ReplayEngine:
    """Deterministic replay engine."""
    
    def __init__(
        self,
        surface: Surface,
        guardrails: GuardrailEngine,
        logger: StructuredLogger,
        evidence: EvidenceCollector,
        stuck_detector: StuckDetector,
        handoff_manager: HandoffManager
    ):
        self.surface = surface
        self.guardrails = guardrails
        self.logger = logger
        self.evidence = evidence
        self.stuck_detector = stuck_detector
        self.handoff_manager = handoff_manager
    
    async def replay(
        self,
        artifact: CapabilityArtifact,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Replay artifact deterministically.
        
        Three-tier error handling:
        1. Business outcomes (expected, not errors)
        2. Recoverable conditions (retry, dismiss dialog)
        3. Hard failures (stop and report)
        """
        execution_id = f"replay_{artifact.artifact_id}_{int(datetime.utcnow().timestamp())}"
        self.logger.info("replay_started", artifact_id=artifact.artifact_id, execution_id=execution_id)
        
        # Validate parameters
        validation_errors = self._validate_parameters(artifact, parameters)
        if validation_errors:
            return ExecutionResult(
                status=ExecutionStatus.HARD_FAILURE,
                artifact_id=artifact.artifact_id,
                execution_id=execution_id,
                error_type="validation_error",
                error_message="; ".join(validation_errors)
            )
        
        # Navigate to entry point
        await self.surface.navigate(artifact.entry_point)
        
        execution_steps: List[ExecutionStep] = []
        outputs: Dict[str, Any] = {}
        
        # Execute each step
        for step in artifact.steps:
            step_start = datetime.utcnow()
            
            # Check if stuck
            if self.stuck_detector.is_stuck(await self.surface.get_state()):
                self.logger.warning("stuck_detected", step_id=step.step_id)
                
                # Escalate to human
                escalation_result = await self.handoff_manager.escalate(
                    artifact_id=artifact.artifact_id,
                    step_id=step.step_id,
                    reason="Stuck - same state repeated",
                    context={"step": step.step_id}
                )
                
                if escalation_result.resumed:
                    self.logger.info("resumed_after_escalation", step_id=step.step_id)
                    continue
                else:
                    return ExecutionResult(
                        status=ExecutionStatus.ESCALATED,
                        artifact_id=artifact.artifact_id,
                        execution_id=execution_id,
                        steps=execution_steps,
                        escalation_reason="Stuck state - human intervention required"
                    )
            
            # Execute step with retries
            step_result = await self._execute_step(step, parameters, outputs)
            
            step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
            
            execution_steps.append(ExecutionStep(
                step_id=step.step_id,
                action=step.action.value,
                status=step_result["status"],
                duration_ms=step_duration,
                error_message=step_result.get("error"),
                screenshot_path=step_result.get("screenshot")
            ))
            
            # Handle step outcome
            if step_result["status"] == ExecutionStatus.BUSINESS_OUTCOME:
                # Expected business outcome (e.g., "member not found")
                return ExecutionResult(
                    status=ExecutionStatus.BUSINESS_OUTCOME,
                    artifact_id=artifact.artifact_id,
                    execution_id=execution_id,
                    steps=execution_steps,
                    business_outcome=step_result["outcome"]
                )
            
            elif step_result["status"] == ExecutionStatus.HARD_FAILURE:
                # Unrecoverable error
                screenshot_path = await self.evidence.save_screenshot(
                    self.surface.screenshot,
                    f"failure_step_{step.step_id}"
                )
                
                return ExecutionResult(
                    status=ExecutionStatus.HARD_FAILURE,
                    artifact_id=artifact.artifact_id,
                    execution_id=execution_id,
                    steps=execution_steps,
                    error_type=step_result.get("error_type", "execution_error"),
                    error_message=step_result.get("error", "Unknown error"),
                    failed_step_id=step.step_id,
                    evidence_dir=screenshot_path
                )
            
            # Collect outputs
            if step.output_ref and "value" in step_result:
                outputs[step.output_ref] = step_result["value"]
        
        # Verify final checkpoint
        checkpoint_valid = await self._verify_checkpoint(artifact.final_checkpoint)
        
        if not checkpoint_valid:
            return ExecutionResult(
                status=ExecutionStatus.HARD_FAILURE,
                artifact_id=artifact.artifact_id,
                execution_id=execution_id,
                steps=execution_steps,
                error_type="checkpoint_failed",
                error_message="Final checkpoint verification failed"
            )
        
        # Success
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            artifact_id=artifact.artifact_id,
            execution_id=execution_id,
            steps=execution_steps,
            outputs=outputs
        )
    
    async def _execute_step(
        self,
        step,
        parameters: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step with retry logic."""
        
        for attempt in range(step.retry_count):
            try:
                # Resolve parameter reference
                value = step.value
                if step.parameter_ref:
                    value = parameters.get(step.parameter_ref, value)
                
                # Execute action
                if step.action == ActionType.CLICK:
                    await self._click_with_fallback(step.locator)
                
                elif step.action == ActionType.TYPE:
                    await self._type_with_fallback(step.locator, value)
                
                elif step.action == ActionType.NAVIGATE:
                    await self.surface.navigate(value)
                
                elif step.action == ActionType.WAIT:
                    await asyncio.sleep(step.timeout_ms / 1000)
                
                elif step.action == ActionType.EXTRACT:
                    extracted = await self._extract_with_fallback(step.locator)
                    return {
                        "status": ExecutionStatus.SUCCESS,
                        "value": extracted
                    }
                
                elif step.action == ActionType.CHECKPOINT:
                    valid = await self._verify_checkpoint_step(step)
                    if not valid:
                        # Check if this is an expected error
                        if step.expected_errors:
                            outcome = await self._detect_business_outcome(step.expected_errors)
                            if outcome:
                                return {
                                    "status": ExecutionStatus.BUSINESS_OUTCOME,
                                    "outcome": outcome
                                }
                        
                        raise Exception("Checkpoint failed")
                
                # Success
                return {"status": ExecutionStatus.SUCCESS}
            
            except Exception as e:
                self.logger.warning(
                    "step_retry",
                    step_id=step.step_id,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                if attempt == step.retry_count - 1:
                    # Final attempt failed
                    if step.on_error == "escalate":
                        return {
                            "status": ExecutionStatus.ESCALATED,
                            "error": str(e)
                        }
                    else:
                        return {
                            "status": ExecutionStatus.HARD_FAILURE,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                
                # Wait before retry
                await asyncio.sleep(1)
        
        return {"status": ExecutionStatus.HARD_FAILURE, "error": "Max retries exceeded"}
    
    async def _click_with_fallback(self, locator) -> None:
        """Click with fallback strategies."""
        strategies = [locator.strategy.value] + [s for s in locator.fallbacks]
        
        for strategy in strategies:
            try:
                await self.surface.click(locator.primary, strategy)
                return
            except Exception as e:
                self.logger.debug("locator_fallback", strategy=strategy, error=str(e))
                continue
        
        raise Exception(f"All locator strategies failed for: {locator.description}")
    
    async def _type_with_fallback(self, locator, text: str) -> None:
        """Type with fallback strategies."""
        strategies = [locator.strategy.value] + [s for s in locator.fallbacks]
        
        for strategy in strategies:
            try:
                await self.surface.type_text(locator.primary, strategy, text)
                return
            except Exception:
                continue
        
        raise Exception(f"All locator strategies failed for: {locator.description}")
    
    async def _extract_with_fallback(self, locator) -> str:
        """Extract text with fallback strategies."""
        strategies = [locator.strategy.value] + [s for s in locator.fallbacks]
        
        for strategy in strategies:
            try:
                return await self.surface.extract_text(locator.primary, strategy)
            except Exception:
                continue
        
        raise Exception(f"All locator strategies failed for: {locator.description}")
    
    async def _verify_checkpoint(self, checkpoint) -> bool:
        """Verify checkpoint condition."""
        try:
            element = await self.surface.find_element(
                checkpoint.locator.primary,
                checkpoint.locator.strategy.value
            )
            
            if not element:
                return False
            
            # Parse expected state
            if checkpoint.expected_state == "visible":
                return element.visible
            elif checkpoint.expected_state.startswith("contains:"):
                text = checkpoint.expected_state.split(":", 1)[1]
                element_text = await self.surface.extract_text(
                    checkpoint.locator.primary,
                    checkpoint.locator.strategy.value
                )
                return text in element_text
            
            return True
        
        except Exception as e:
            self.logger.error("checkpoint_error", error=str(e))
            return False
    
    async def _verify_checkpoint_step(self, step) -> bool:
        """Verify checkpoint from step."""
        if not step.checkpoint:
            return True
        
        # Simplified checkpoint verification
        return await self.surface.wait_for(
            step.locator.primary,
            step.locator.strategy.value,
            step.timeout_ms
        )
    
    async def _detect_business_outcome(self, expected_errors: list) -> Optional[str]:
        """Detect if current state matches an expected business outcome."""
        state = await self.surface.get_state()
        
        # Check for known error messages in page
        for error_pattern in expected_errors:
            if error_pattern.lower() in state.accessibility_tree.lower():
                return error_pattern
        
        return None
    
    def _validate_parameters(
        self,
        artifact: CapabilityArtifact,
        parameters: Dict[str, Any]
    ) -> list[str]:
        """Validate input parameters."""
        errors = []
        
        for param in artifact.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"Missing required parameter: {param.name}")
            
            if param.name in parameters:
                # Type validation (simplified)
                value = parameters[param.name]
                if param.type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Parameter {param.name} must be a number")
        
        return errors
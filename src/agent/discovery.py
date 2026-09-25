"""LLM-driven discovery agent - observe, decide, act loop."""

import anthropic
from typing import Dict, Any, List, Optional
import json
import asyncio
from ..models.artifact import (
    CapabilityArtifact,
    Step,
    ActionType,
    Locator,
    LocatorStrategy,
    Parameter,
    Output,
    Checkpoint,
)
from ..models.execution import ExecutionResult, ExecutionStatus, ExecutionStep
from ..surfaces.base import Surface
from ..safety.guardrails import GuardrailEngine
from ..observability.logger import StructuredLogger
from ..observability.evidence import EvidenceCollector
from .prompts import DISCOVERY_SYSTEM_PROMPT, DISCOVERY_USER_PROMPT


class DiscoveryAgent:
    """LLM-driven discovery agent."""

    def __init__(
        self,
        client: anthropic.Anthropic,
        surface: Surface,
        guardrails: GuardrailEngine,
        logger: StructuredLogger,
        evidence: EvidenceCollector,
        max_steps: int = 50,
    ):
        self.client = client
        self.surface = surface
        self.guardrails = guardrails
        self.logger = logger
        self.evidence = evidence
        self.max_steps = max_steps

    async def discover(
        self, goal: str, entry_point: str, parameters: Optional[Dict[str, Any]] = None
    ) -> tuple[CapabilityArtifact, ExecutionResult]:
        """
        Run LLM-driven discovery to accomplish goal.

        Returns:
            (artifact, execution_result)
        """
        self.logger.info("discovery_started", goal=goal, entry_point=entry_point)

        # Initialize
        await self.surface.navigate(entry_point)
        steps_taken: List[Step] = []
        execution_steps: List[ExecutionStep] = []
        step_count = 0

        # Conversation history
        messages = []

        while step_count < self.max_steps:
            step_count += 1

            # OBSERVE: Get current state
            # OBSERVE: Get current state
            state = await self.surface.get_state()
            # CHANGE: Fixed method call - added parentheses and path argument
            screenshot_path = await self.evidence.save_screenshot(
                lambda path: self.surface.screenshot(path), f"step_{step_count}"
            )

            # Build prompt
            user_message = DISCOVERY_USER_PROMPT.format(
                goal=goal,
                step_number=step_count,
                url=state.url,
                accessibility_tree=state.accessibility_tree[:5000],  # Truncate
                parameters=json.dumps(parameters or {}),
            )

            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": state.screenshot_base64,
                            },
                        },
                    ],
                }
            )

            # DECIDE: Ask LLM what to do
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=DISCOVERY_SYSTEM_PROMPT,
                messages=messages,
            )

            assistant_message = response.content[0].text
            messages.append({"role": "assistant", "content": assistant_message})

            # Parse action from response
            action_data = self._parse_action(assistant_message)

            if not action_data:
                self.logger.error("failed_to_parse_action", response=assistant_message)
                break

            # Check if goal achieved
            if action_data.get("action") == "goal_achieved":
                self.logger.info("goal_achieved", step=step_count)

                # Build artifact
                artifact = self._build_artifact(
                    goal, entry_point, steps_taken, action_data, parameters
                )

                result = ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    artifact_id=artifact.artifact_id,
                    execution_id=f"discovery_{artifact.artifact_id}",
                    steps=execution_steps,
                    outputs=action_data.get("outputs", {}),
                )

                return artifact, result

            # Validate action against guardrails
            if not self.guardrails.validate_action(action_data):
                self.logger.error("guardrail_violation", action=action_data)
                break

            # ACT: Execute action
            try:
                await self._execute_action(action_data)

                # Record step
                step = self._action_to_step(action_data, step_count)
                steps_taken.append(step)

                execution_steps.append(
                    ExecutionStep(
                        step_id=step_count,
                        action=action_data["action"],
                        status=ExecutionStatus.SUCCESS,
                        screenshot_path=screenshot_path,
                    )
                )

                self.logger.info(
                    "step_executed", step=step_count, action=action_data["action"]
                )

            except Exception as e:
                self.logger.error("step_failed", step=step_count, error=str(e))
                execution_steps.append(
                    ExecutionStep(
                        step_id=step_count,
                        action=action_data["action"],
                        status=ExecutionStatus.HARD_FAILURE,
                        error_message=str(e),
                        screenshot_path=screenshot_path,
                    )
                )
                break

        # If we get here, we didn't achieve the goal
        self.logger.warning("discovery_incomplete", steps=step_count)

        # Return partial artifact
        artifact = CapabilityArtifact(
            artifact_id=f"incomplete_{entry_point.replace('/', '_')}",
            name=f"Incomplete: {goal}",
            description=f"Partial discovery for: {goal}",
            entry_point=entry_point,
            steps=steps_taken,
        )

        result = ExecutionResult(
            status=ExecutionStatus.HARD_FAILURE,
            artifact_id=artifact.artifact_id,
            execution_id=f"discovery_{artifact.artifact_id}",
            steps=execution_steps,
            error_message="Max steps reached without achieving goal",
        )

        return artifact, result

    def _parse_action(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse action from LLM response."""
        try:
            # Look for JSON block in response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
        except Exception as e:
            self.logger.error("parse_error", error=str(e))

        return None

    async def _execute_action(self, action_data: Dict[str, Any]) -> None:
        """Execute a single action."""
        action = action_data["action"]

        if action == "click":
            await self.surface.click(
                action_data["locator"], action_data.get("strategy", "accessibility")
            )
        elif action == "type":
            await self.surface.type_text(
                action_data["locator"],
                action_data.get("strategy", "accessibility"),
                action_data["value"],
            )
        elif action == "navigate":
            await self.surface.navigate(action_data["url"])
        elif action == "wait":
            await asyncio.sleep(action_data.get("duration_ms", 1000) / 1000)

    def _action_to_step(self, action_data: Dict[str, Any], step_id: int) -> Step:
        """Convert action data to Step."""
        locator = None
        if "locator" in action_data:
            locator = Locator(
                strategy=LocatorStrategy(action_data.get("strategy", "accessibility")),
                primary=action_data["locator"],
                description=action_data.get("description", ""),
            )

        return Step(
            step_id=step_id,
            action=ActionType(action_data["action"]),
            locator=locator,
            value=action_data.get("value"),
            parameter_ref=action_data.get("parameter_ref"),
        )

    def _build_artifact(
        self,
        goal: str,
        entry_point: str,
        steps: List[Step],
        final_action: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> CapabilityArtifact:
        """Build capability artifact from successful discovery."""

        # Extract parameters
        params = []
        if parameters:
            for name, value in parameters.items():
                params.append(
                    Parameter(
                        name=name,
                        type="string",  # Simplified
                        description=f"Input parameter: {name}",
                    )
                )

        # Extract outputs
        outputs = []
        if "outputs" in final_action:
            for name, value in final_action["outputs"].items():
                outputs.append(
                    Output(
                        name=name,
                        type="string",  # Simplified
                        description=f"Output field: {name}",
                        extraction_path=f"$.{name}",
                    )
                )

        # Build checkpoint
        checkpoint = Checkpoint(
            description="Goal achieved",
            locator=Locator(
                strategy=LocatorStrategy.ACCESSIBILITY,
                primary=final_action.get("checkpoint_locator", ""),
                description="Final state verification",
            ),
            expected_state="visible",
        )

        return CapabilityArtifact(
            artifact_id=f"cap_{entry_point.replace('/', '_')}_{len(steps)}",
            name=goal,
            description=f"Automated capability: {goal}",
            entry_point=entry_point,
            parameters=params,
            outputs=outputs,
            steps=steps,
            final_checkpoint=checkpoint,
        )

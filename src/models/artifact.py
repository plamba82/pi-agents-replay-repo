"""Capability artifact schema - the reusable automation contract."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
import json


class LocatorStrategy(Enum):
    """Element targeting strategy."""

    ACCESSIBILITY = "accessibility"  # Accessibility tree (role + name)
    VISUAL = "visual"  # Visual landmark + offset
    DOM = "dom"  # CSS/XPath selector
    TEXT = "text"  # Visible text content
    COMPOSITE = "composite"  # Multiple strategies with fallback


class ActionType(Enum):
    """Supported action types."""

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    WAIT = "wait"
    EXTRACT = "extract"
    CHECKPOINT = "checkpoint"


@dataclass
class Locator:
    """Multi-strategy element locator."""

    strategy: LocatorStrategy
    primary: str  # Primary selector
    fallbacks: List[str] = field(default_factory=list)
    description: str = ""  # Human-readable description

    # Strategy-specific metadata
    accessibility_role: Optional[str] = None
    accessibility_name: Optional[str] = None
    visual_landmark: Optional[str] = None
    visual_offset: Optional[Dict[str, int]] = None


@dataclass
class Step:
    """Single automation step."""

    step_id: int
    action: ActionType
    locator: Optional[Locator] = None
    value: Optional[str] = None  # For type/select actions
    parameter_ref: Optional[str] = None  # Reference to input parameter
    output_ref: Optional[str] = None  # Reference to output field
    checkpoint: Optional[str] = None  # Success condition
    timeout_ms: int = 30000
    retry_count: int = 3

    # Error handling
    on_error: Literal["fail", "retry", "skip", "escalate"] = "fail"
    expected_errors: List[str] = field(default_factory=list)  # Known business outcomes


@dataclass
class Parameter:
    """Input parameter definition."""

    name: str
    type: Literal["string", "number", "boolean"]
    description: str
    required: bool = True
    default: Optional[Any] = None
    validation_pattern: Optional[str] = None  # Regex for validation


@dataclass
class Output:
    """Output field definition."""

    name: str
    type: Literal["string", "number", "boolean", "object"]
    description: str
    extraction_path: str  # JSONPath or similar


@dataclass
class Checkpoint:
    """Success verification condition."""

    description: str
    locator: Locator
    expected_state: str  # "visible", "contains:text", "count:N"


@dataclass
class CapabilityArtifact:
    """
    Versioned, typed capability artifact.

    This is the contract between discovery and replay - a reusable,
    reviewable automation that an AI agent can invoke.
    """

    # Metadata
    artifact_id: str
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Capability contract
    name: str = "test"
    description: str = "test"
    entry_point: str = "test"  # URL or app identifier

    # I/O contract
    parameters: List[Parameter] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)

    # Execution flow
    steps: List[Step] = field(default_factory=list)
    final_checkpoint: Checkpoint = None

    # Multi-tenant support
    tenant_id: Optional[str] = None
    base_artifact_id: Optional[str] = None  # For tenant-specific overrides

    # Metadata for reuse
    tags: List[str] = field(default_factory=list)
    estimated_duration_ms: int = 0

    def to_json(self) -> str:
        """Serialize to JSON."""

        # CHANGE: Custom serialization to handle enums properly
        def enum_serializer(obj):
            if isinstance(obj, Enum):
                return obj.value  # Return enum value instead of string representation
            return str(obj)

        return json.dumps(asdict(self), indent=2, default=enum_serializer)

    @classmethod
    def from_json(cls, json_str: str) -> "CapabilityArtifact":
        """Deserialize from JSON."""
        data = json.loads(json_str)

        # Reconstruct nested objects
        data["parameters"] = [Parameter(**p) for p in data.get("parameters", [])]
        data["outputs"] = [Output(**o) for o in data.get("outputs", [])]

        steps = []
        for s in data.get("steps", []):
            if s.get("locator"):
                # CHANGE: Extract enum value from string representation (e.g., "LocatorStrategy.ACCESSIBILITY" -> "accessibility")
                strategy_str = s["locator"]["strategy"]
                if "." in strategy_str:
                    # Handle "LocatorStrategy.ACCESSIBILITY" format
                    strategy_value = strategy_str.split(".")[-1].lower()
                else:
                    # Handle "accessibility" format
                    strategy_value = strategy_str

                s["locator"] = Locator(
                    strategy=LocatorStrategy(strategy_value),
                    **{k: v for k, v in s["locator"].items() if k != "strategy"},
                )
            # CHANGE: Extract enum value from action string representation
            action_str = s["action"]
            if "." in action_str:
                # Handle "ActionType.CLICK" format
                action_value = action_str.split(".")[-1].lower()
            else:
                # Handle "click" format
                action_value = action_str

            s["action"] = ActionType(action_value)
            steps.append(Step(**s))
        data["steps"] = steps

        if data.get("final_checkpoint"):
            cp = data["final_checkpoint"]
            # CHANGE: Extract enum value from checkpoint locator strategy
            strategy_str = cp["locator"]["strategy"]
            if "." in strategy_str:
                strategy_value = strategy_str.split(".")[-1].lower()
            else:
                strategy_value = strategy_str

            cp["locator"] = Locator(
                strategy=LocatorStrategy(strategy_value),
                **{k: v for k, v in cp["locator"].items() if k != "strategy"},
            )
            data["final_checkpoint"] = Checkpoint(**cp)

        return cls(**data)

    def validate(self) -> List[str]:
        """Validate artifact integrity."""
        errors = []

        if not self.name:
            errors.append("name is required")
        if not self.entry_point:
            errors.append("entry_point is required")
        if not self.steps:
            errors.append("steps cannot be empty")
        if not self.final_checkpoint:
            errors.append("final_checkpoint is required")

        # Validate parameter references
        param_names = {p.name for p in self.parameters}
        for step in self.steps:
            if step.parameter_ref and step.parameter_ref not in param_names:
                errors.append(
                    f"Step {step.step_id}: unknown parameter '{step.parameter_ref}'"
                )

        return errors

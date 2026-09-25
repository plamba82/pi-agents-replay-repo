"""Execution result types - three-tier error taxonomy."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from enum import Enum


class ExecutionStatus(Enum):
    """Execution outcome classification."""
    SUCCESS = "success"                    # Goal achieved
    BUSINESS_OUTCOME = "business_outcome"  # Expected non-success (e.g., "not found")
    RECOVERABLE_ERROR = "recoverable"      # Transient, can retry
    HARD_FAILURE = "failure"              # Unrecoverable error
    ESCALATED = "escalated"               # Human intervention required


@dataclass
class ExecutionStep:
    """Record of a single step execution."""
    step_id: int
    action: str
    status: ExecutionStatus
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: int = 0
    
    # Evidence
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    
    # What was observed
    observed_state: Optional[str] = None
    expected_state: Optional[str] = None


@dataclass
class ExecutionResult:
    """
    Structured execution result.
    
    Distinguishes:
    - Success with outputs
    - Expected business outcomes (not errors)
    - Recoverable conditions
    - Hard failures with debug context
    """
    
    status: ExecutionStatus
    artifact_id: str
    execution_id: str
    
    # Timing
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    duration_ms: int = 0
    
    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    business_outcome: Optional[str] = None  # e.g., "member_not_found"
    
    # Execution trace
    steps: List[ExecutionStep] = field(default_factory=list)
    
    # Error details (for failures)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    failed_step_id: Optional[int] = None
    
    # Evidence
    evidence_dir: Optional[str] = None
    
    # Escalation
    escalation_reason: Optional[str] = None
    escalation_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "artifact_id": self.artifact_id,
            "execution_id": self.execution_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "outputs": self.outputs,
            "business_outcome": self.business_outcome,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error_message": s.error_message
                }
                for s in self.steps
            ],
            "error_type": self.error_type,
            "error_message": self.error_message,
            "failed_step_id": self.failed_step_id,
            "escalation_reason": self.escalation_reason
        }
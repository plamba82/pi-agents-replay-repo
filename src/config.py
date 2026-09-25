"""Configuration and safety guardrails."""
from dataclasses import dataclass, field
from typing import Set, List
from enum import Enum
import os
from dotenv import load_dotenv

# CHANGE: Load .env file before accessing environment variables
load_dotenv()


class ActionRisk(Enum):
    """Action risk classification."""
    SAFE = "safe"              # Read-only, reversible
    MODERATE = "moderate"      # Writes with undo
    RISKY = "risky"           # Irreversible, requires confirmation


@dataclass
class SafetyConfig:
    """Safety and policy configuration."""
    
    # Domain allowlist
    allowed_domains: Set[str] = field(default_factory=lambda: {
        "localhost",
        "127.0.0.1",
        # "demo.test.ai"
    })
    
    # Route patterns (regex)
    allowed_routes: List[str] = field(default_factory=lambda: [
        r"^/search.*",
        r"^/member/\d+$",
        r"^/account/.*"
    ])
    
    # Action classification
    safe_actions: Set[str] = field(default_factory=lambda: {
        "navigate", "click", "read", "scroll", "wait"
    })
    
    risky_actions: Set[str] = field(default_factory=lambda: {
        "submit_transaction", "delete", "approve", "transfer"
    })
    
    # PII patterns for redaction
    pii_patterns: List[str] = field(default_factory=lambda: [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{16}\b",              # Card number
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"  # Email
    ])
    
    # Execution limits
    max_steps: int = 20
    step_timeout_seconds: int = 30
    total_timeout_seconds: int = 300
    
    # Escalation thresholds
    max_retries_before_escalation: int = 2
    stuck_detection_threshold: int = 3  # Same state N times


@dataclass
class Config:
    """Application configuration."""
    
    # LLM
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = "claude-3-5-sonnet-20240620"
    
    # Automation
    browser: str = "chromium"
    headless: bool = False
    
    # Storage
    artifacts_dir: str = "artifacts"
    evidence_dir: str = "evidence"
    
    # Safety
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    def validate(self) -> None:
        """Validate configuration."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
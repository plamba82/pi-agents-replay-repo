"""Safety guardrails - allowlist enforcement and action validation."""
from typing import Dict, Any
import re
from urllib.parse import urlparse
from ..config import SafetyConfig, ActionRisk


class GuardrailEngine:
    """Enforce safety policies."""
    
    def __init__(self, config: SafetyConfig):
        self.config = config
    
    def validate_action(self, action_data: Dict[str, Any]) -> bool:
        """Validate action against guardrails."""
        
        # Check action type
        action = action_data.get("action")
        
        if action in self.config.risky_actions:
            # Risky actions require explicit confirmation
            # In production, this would trigger approval workflow
            return False
        
        # Validate URL for navigate actions
        if action == "navigate":
            url = action_data.get("url", "")
            if not self._is_allowed_url(url):
                return False
        
        return True
    
    def _is_allowed_url(self, url: str) -> bool:
        """Check if URL is in allowlist."""
        parsed = urlparse(url)
        
        # Check domain
        if parsed.netloc not in self.config.allowed_domains:
            return False
        
        # Check route patterns
        for pattern in self.config.allowed_routes:
            if re.match(pattern, parsed.path):
                return True
        
        return False
    
    def classify_action_risk(self, action: str) -> ActionRisk:
        """Classify action risk level."""
        if action in self.config.safe_actions:
            return ActionRisk.SAFE
        elif action in self.config.risky_actions:
            return ActionRisk.RISKY
        else:
            return ActionRisk.MODERATE
"""Stuck state detection for human escalation."""
from typing import Dict, Any
from collections import deque
from ..surfaces.base import SurfaceState


class StuckDetector:
    """Detect when automation is stuck in same state."""
    
    def __init__(self, threshold: int = 5):
        self.threshold = threshold
        self.state_history = deque(maxlen=threshold)
    
    def is_stuck(self, state: SurfaceState) -> bool:
        """Check if stuck in same state."""
        
        # Create state fingerprint
        fingerprint = self._fingerprint(state)
        
        self.state_history.append(fingerprint)
        
        # Check if all recent states are identical
        if len(self.state_history) >= self.threshold:
            return len(set(self.state_history)) == 1
        
        return False
    
    def _fingerprint(self, state: SurfaceState) -> str:
        """Create state fingerprint for comparison."""
        return f"{state.url}:{state.title}:{hash(state.accessibility_tree[:1000])}"
    
    def reset(self) -> None:
        """Reset detection state."""
        self.state_history.clear()
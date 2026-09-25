"""Evidence collection for debugging and audit."""
import os
from typing import Callable
from datetime import datetime


class EvidenceCollector:
    """Collect screenshots and traces for evidence."""
    
    def __init__(self, evidence_dir: str):
        self.evidence_dir = evidence_dir
        os.makedirs(evidence_dir, exist_ok=True)
        os.makedirs(f"{evidence_dir}/screenshots", exist_ok=True)
    
    async def save_screenshot(
        self,
        screenshot_func: Callable,
        name: str
    ) -> str:
        """Save screenshot and return path."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = f"{self.evidence_dir}/screenshots/{filename}"
        
        await screenshot_func(path)
        
        return path
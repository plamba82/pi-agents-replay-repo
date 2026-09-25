"""Surface abstraction protocol - supports web, desktop, accessibility."""
from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SurfaceState:
    """Current state of the surface."""
    url: Optional[str] = None
    title: Optional[str] = None
    accessibility_tree: Optional[str] = None
    screenshot_base64: Optional[str] = None
    dom_snapshot: Optional[str] = None
    
    # For desktop apps
    window_title: Optional[str] = None
    process_name: Optional[str] = None


@dataclass
class Element:
    """Unified element representation."""
    locator: str
    role: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    bounds: Optional[Dict[str, int]] = None  # x, y, width, height
    visible: bool = True


class Surface(Protocol):
    """
    Surface abstraction protocol.
    
    Implementations: WebSurface (Playwright), DesktopSurface (OS automation),
    AccessibilitySurface (platform accessibility APIs).
    """
    
    async def navigate(self, target: str) -> None:
        """Navigate to target (URL, app, window)."""
        ...
    
    async def get_state(self) -> SurfaceState:
        """Capture current surface state."""
        ...
    
    async def find_element(self, locator: str, strategy: str) -> Optional[Element]:
        """Find element using specified strategy."""
        ...
    
    async def click(self, locator: str, strategy: str) -> None:
        """Click element."""
        ...
    
    async def type_text(self, locator: str, strategy: str, text: str) -> None:
        """Type text into element."""
        ...
    
    async def extract_text(self, locator: str, strategy: str) -> str:
        """Extract text from element."""
        ...
    
    async def wait_for(self, locator: str, strategy: str, timeout_ms: int) -> bool:
        """Wait for element to appear."""
        ...
    
    async def screenshot(self, path: str) -> None:
        """Capture screenshot."""
        ...
    
    async def close(self) -> None:
        """Clean up resources."""
        ...
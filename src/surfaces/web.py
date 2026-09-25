"""Playwright-based web surface implementation."""
import os
import tempfile

from playwright.async_api import async_playwright, Page, Browser, Playwright
from typing import Optional
import base64
import asyncio
from .base import Surface, SurfaceState, Element


class WebSurface:
    """Web surface using Playwright."""
    
    def __init__(self, browser_type: str = "chromium", headless: bool = False):
        self.browser_type = browser_type
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # CHANGE: Start playwright with explicit initialization
        self._playwright = await async_playwright().start()
        
        # CHANGE: Get browser launcher by type with explicit handling
        if self.browser_type == "chromium":
            browser_launcher = self._playwright.chromium
        elif self.browser_type == "firefox":
            browser_launcher = self._playwright.firefox
        elif self.browser_type == "webkit":
            browser_launcher = self._playwright.webkit
        else:
            browser_launcher = self._playwright.chromium
        
        # CHANGE: Comprehensive macOS crash prevention flags
        launch_args = [
            '--disable-dev-shm-usage',      # Prevent shared memory crashes
            '--no-sandbox',                  # Disable sandboxing (macOS compatibility)
            '--disable-setuid-sandbox',      # Additional sandbox disable
            '--disable-gpu',                 # Disable GPU acceleration (common crash source)
            '--disable-software-rasterizer', # Prevent software rendering crashes
            '--disable-extensions',          # Disable extensions
            '--disable-background-networking', # Reduce background activity
            '--disable-sync',                # Disable Chrome sync
            '--metrics-recording-only',      # Minimal metrics
            '--no-first-run',                # Skip first-run experience
            '--safebrowsing-disable-auto-update', # Disable safe browsing updates
            '--disable-features=TranslateUI', # Disable translate
            '--disable-blink-features=AutomationControlled', # Hide automation
        ]
        
        # CHANGE: Retry logic for browser launch with exponential backoff
        max_retries = 3
        retry_delay = 1  # seconds
        # CHANGE: Use system temp directory for profile
        user_data_dir = os.path.join(tempfile.gettempdir(), "playwright-chrome-profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # CHANGE: Specify Chrome executable path explicitly (macOS ARM64)
        # For Intel Macs, use: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                
        for attempt in range(max_retries):
            try:
                # CHANGE: Launch browser with comprehensive error handling
                self._browser = await browser_launcher.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=self.headless,
                    args=launch_args,
                    executable_path=chrome_path,
                    # CHANGE: Additional launch options for stability
                    timeout=60000,  # 60 second timeout
                    slow_mo=50 if not self.headless else 0,  # Slow down for visibility
                )
                
                # CHANGE: Verify browser is actually running
                if not self._browser:
                    raise RuntimeError("Browser launched but returned None")
                
                # CHANGE: Create new page with timeout
                self._page = await asyncio.wait_for(
                    self._browser.new_page(),
                    timeout=30.0
                )
                
                # CHANGE: Verify page is ready
                if not self._page:
                    raise RuntimeError("Page created but returned None")
                
                # CHANGE: Set default timeouts
                self._page.set_default_timeout(30000)
                self._page.set_default_navigation_timeout(30000)
                
                # Success - break retry loop
                print(f"✅ Browser launched successfully (attempt {attempt + 1}/{max_retries})")
                return self
                
            except Exception as e:
                print(f"⚠️  Browser launch attempt {attempt + 1}/{max_retries} failed: {e}")
                
                # CHANGE: Clean up failed resources
                await self._cleanup_failed_launch()
                
                if attempt < max_retries - 1:
                    # CHANGE: Wait before retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"   Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    # CHANGE: Final attempt failed - provide diagnostic info
                    error_msg = (
                        f"Failed to launch browser after {max_retries} attempts.\n"
                        f"Last error: {e}\n"
                        f"Browser type: {self.browser_type}\n"
                        f"Headless: {self.headless}\n"
                        f"\nTroubleshooting steps:\n"
                        f"1. Kill existing Chromium processes: pkill -9 chromium\n"
                        f"2. Reinstall Playwright browsers: playwright install chromium --force\n"
                        f"3. Try Firefox instead: Edit config.py, set browser='firefox'\n"
                        f"4. Check system resources: Activity Monitor (memory/CPU)\n"
                        f"5. Try headless mode: Add --headless flag to command"
                    )
                    raise RuntimeError(error_msg) from e
        
        return self
    
    async def _cleanup_failed_launch(self):
        """Clean up resources after failed launch attempt."""
        # CHANGE: Safely close page if it exists
        if self._page:
            try:
                await asyncio.wait_for(self._page.close(), timeout=5.0)
            except Exception:
                pass
            self._page = None
        
        # CHANGE: Safely close browser if it exists
        if self._browser:
            try:
                await asyncio.wait_for(self._browser.close(), timeout=5.0)
            except Exception:
                pass
            self._browser = None
        
        # CHANGE: Don't stop playwright here - we might retry
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def navigate(self, target: str) -> None:
        """Navigate to URL."""
        await self._page.goto(target, wait_until="networkidle")
    
    async def get_state(self) -> SurfaceState:
        """Capture current page state."""
        
                # Get accessibility tree
        # accessibility_tree = await self._page.accessibility.snapshot()
        # CHANGE: Build accessibility info from ARIA attributes instead of deprecated snapshot()
        try:
            # Get all elements with ARIA roles
            elements = await self._page.locator('[role]').all()
            accessibility_info = []
            
            for elem in elements[:50]:  # Limit to first 50 to avoid performance issues
                try:
                    role = await elem.get_attribute('role')
                    name = await elem.get_attribute('aria-label') or await elem.inner_text()
                    accessibility_info.append(f"{role}: {name[:50]}")  # Truncate long names
                except Exception:
                    continue
            
            accessibility_tree = "\n".join(accessibility_info)
        except Exception:
            # CHANGE: Fallback to empty string if accessibility extraction fails
            accessibility_tree = ""
            # Get screenshot
        screenshot_bytes = await self._page.screenshot()
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
        
        return SurfaceState(
            url=self._page.url,
            title=await self._page.title(),
            accessibility_tree=accessibility_tree,
            screenshot_base64=screenshot_base64
        )
    
    async def find_element(self, locator: str, strategy: str) -> Optional[Element]:
        """Find element using strategy."""
        try:
            if strategy == "accessibility":
                # Use role and name
                parts = locator.split(":", 1)
                role = parts[0]
                name = parts[1] if len(parts) > 1 else None
                element = self._page.get_by_role(role, name=name)
            elif strategy == "text":
                element = self._page.get_by_text(locator)
            else:  # DOM selector
                element = self._page.locator(locator)
            
            if await element.count() > 0:
                box = await element.first.bounding_box()
                return Element(
                    locator=locator,
                    visible=await element.first.is_visible(),
                    bounds=box
                )
        except Exception:
            pass
        
        return None
    
    async def click(self, locator: str, strategy: str) -> None:
        """Click element."""
        element = await self._get_locator(locator, strategy)
        await element.click()
    
    async def type_text(self, locator: str, strategy: str, text: str) -> None:
        """Type text."""
        element = await self._get_locator(locator, strategy)
        await element.fill(text)
    
    async def extract_text(self, locator: str, strategy: str) -> str:
        """Extract text."""
        element = await self._get_locator(locator, strategy)
        return await element.inner_text()
    
    async def wait_for(self, locator: str, strategy: str, timeout_ms: int) -> bool:
        """Wait for element."""
        try:
            element = await self._get_locator(locator, strategy)
            await element.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False
    
    async def screenshot(self, path: str) -> None:
        """Save screenshot."""
        # CHANGE: Added missing screenshot method
        await self._page.screenshot(path=path)
    
    async def close(self) -> None:
        """Clean up."""
        # CHANGE: Added missing close method with proper cleanup order
        if self._page:
            try:
                await asyncio.wait_for(self._page.close(), timeout=5.0)
            except Exception:
                pass
            self._page = None
        
        if self._browser:
            try:
                await asyncio.wait_for(self._browser.close(), timeout=5.0)
            except Exception:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                await asyncio.wait_for(self._playwright.stop(), timeout=5.0)
            except Exception:
                pass
            self._playwright = None
    
    async def _get_locator(self, locator: str, strategy: str):
        """Get Playwright locator based on strategy."""
        if strategy == "accessibility":
            parts = locator.split(":", 1)
            role = parts[0]
            name = parts[1] if len(parts) > 1 else None
            return self._page.get_by_role(role, name=name)
        elif strategy == "text":
            return self._page.get_by_text(locator)
        else:
            return self._page.locator(locator)
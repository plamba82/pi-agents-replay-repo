import asyncio
import os
import tempfile
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        print("Launching Chromium...")
        
        # CHANGE: Use system temp directory for profile
        user_data_dir = os.path.join(tempfile.gettempdir(), "playwright-chrome-profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # CHANGE: Specify Chrome executable path explicitly (macOS ARM64)
        # For Intel Macs, use: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=chrome_path,  # CHANGE: Explicit path instead of channel
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ],
        )
        
        print("Chromium launched")
        
        page = await context.new_page()
        
        print("Page created")
        
        await page.goto("https://example.com")
        
        print("Page title:", await page.title())
        
        await page.wait_for_timeout(10000)
        
        # CHANGE: Close in proper order
        await page.close()
        await context.close()


asyncio.run(main())
"""
Browser automation agent - Playwright-based form filling and submission
"""
import os
import sys
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("Warning: Playwright not installed. Run: pip install playwright")
    print("Then: python -m playwright install")

logger = logging.getLogger(__name__)


class BrowserAgent:
    """Automate form filling and job portal navigation."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.screenshots_dir = "./autofill/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def start(self):
        """Start browser session."""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            logger.info("Browser started")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
    
    def stop(self):
        """Stop browser session."""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    def navigate_to(self, url: str):
        """Navigate to URL."""
        try:
            self.page.goto(url, timeout=30000)
            logger.info(f"Navigated to {url}")
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
    
    def fill_form(self, field_mappings: Dict[str, str]):
        """
        Fill form fields using field mappings.
        
        Args:
            field_mappings: Dict of {input_selector: value}
        """
        try:
            for selector, value in field_mappings.items():
                self.page.fill(selector, value)
                logger.debug(f"Filled {selector} with {value[:30]}...")
        except Exception as e:
            logger.error(f"Form filling failed: {e}")
    
    def submit_form(self, submit_button_selector: str = "button[type='submit']"):
        """Submit form."""
        try:
            self.page.click(submit_button_selector)
            logger.info("Form submitted")
        except Exception as e:
            logger.error(f"Form submission failed: {e}")
    
    def take_screenshot(self, name: str) -> str:
        """Take screenshot and save."""
        try:
            file_path = os.path.join(self.screenshots_dir, f"{name}.png")
            self.page.screenshot(path=file_path)
            logger.info(f"Screenshot saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def apply_to_job(self, portal_url: str, field_data: Dict[str, str]) -> bool:
        """
        Apply to job by filling and submitting form.
        
        Args:
            portal_url: URL to job application portal
            field_data: Form field values from profile
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Applying to job at {portal_url}")
            
            self.navigate_to(portal_url)
            # Auto-detect and fill form fields
            self.fill_form(field_data)
            self.submit_form()
            self.take_screenshot("submission_confirmation")
            
            return True
        except Exception as e:
            logger.error(f"Job application failed: {e}")
            return False


# Example usage
if __name__ == "__main__":
    agent = BrowserAgent()
    agent.start()
    
    # Example: Navigate and fill form
    # agent.navigate_to("https://example.com/apply")
    # agent.fill_form({
    #     "input[name='fullName']": "John Doe",
    #     "input[name='email']": "john@example.com"
    # })
    # agent.submit_form()
    
    agent.stop()

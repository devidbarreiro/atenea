from playwright.sync_api import sync_playwright
import os

def test_notification_trigger():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load local HTML file
        file_path = os.path.abspath("verification/verify_notification.html")
        page.goto(f"file://{file_path}")

        # Verify initial state
        status = page.locator("#status")
        print(f"Initial status: {status.inner_text()}")

        # Trigger the event
        page.evaluate("simulateNotificationEvent()")

        # Wait for status update
        page.wait_for_function("document.getElementById('status').innerText === 'HTMX Request Triggered!'")

        print(f"Final status: {status.inner_text()}")

        # Take screenshot
        page.screenshot(path="verification/notification_verification.png")

        browser.close()

if __name__ == "__main__":
    test_notification_trigger()

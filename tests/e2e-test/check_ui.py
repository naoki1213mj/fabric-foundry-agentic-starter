import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://app-daj6dri4yf3k3z.azurewebsites.net/")
    time.sleep(3)
    # Get textarea elements
    textareas = page.locator("textarea").all()
    print("Found textareas:", len(textareas))
    for i, ta in enumerate(textareas):
        try:
            placeholder = ta.get_attribute("placeholder")
            print(f'  Textarea {i}: placeholder="{placeholder}"')
        except Exception as e:
            print(f"  Textarea {i}: error - {e}")

    # Also check all buttons
    buttons = page.locator("button").all()
    print(f"\nFound buttons: {len(buttons)}")
    for i, btn in enumerate(buttons[:10]):
        try:
            title = btn.get_attribute("title")
            text = btn.inner_text()[:50] if btn.inner_text() else ""
            print(f'  Button {i}: title="{title}", text="{text}"')
        except Exception as e:
            print(f"  Button {i}: error - {e}")

    browser.close()

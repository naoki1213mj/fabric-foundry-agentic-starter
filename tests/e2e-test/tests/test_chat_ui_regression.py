"""UI regression checks for reasoning/tool toggle rendering."""

import logging
import time

from config.constants import URL
from pages.HomePage import HomePage
from playwright.sync_api import expect

from tests.test_utils import log_test_failure, log_test_summary

logger = logging.getLogger(__name__)


def test_reasoning_tool_toggle_ui_regression(login_logout):
    """
    Best-effort check to ensure reasoning/tool toggles render and expand without UI collapse.
    This test is tolerant if the backend doesn't emit reasoning/tool events.
    """
    page = login_logout
    home = HomePage(page)

    logger.info("Refreshing page to start with a fresh session...")
    page.goto(URL)
    page.wait_for_timeout(3000)

    start_time = time.time()

    try:
        step_times = []

        step_start = time.time()
        home.ask_question_with_retry("在庫最適化のポイントを教えて")
        step_times.append(("Step 1 (Ask question)", time.time() - step_start))

        step_start = time.time()
        reasoning_toggle = page.locator("[data-testid='reasoning-toggle']")
        if reasoning_toggle.count() > 0:
            reasoning_toggle.first.click()
            expect(page.locator("[data-testid='reasoning-content']")).to_be_visible(timeout=15000)
            page.mouse.wheel(0, 120)
            expect(page.locator("[data-testid='reasoning-content']")).to_be_visible(timeout=15000)
        else:
            logger.info("No reasoning toggle found; skipping reasoning checks.")
        step_times.append(("Step 2 (Reasoning toggle)", time.time() - step_start))

        step_start = time.time()
        tool_toggle = page.locator("[data-testid='tool-status-toggle']")
        if tool_toggle.count() > 0:
            tool_toggle.first.click()
            expect(page.locator("[data-testid='tool-status-list']")).to_be_visible(timeout=15000)
            page.mouse.wheel(0, 120)
            expect(page.locator("[data-testid='tool-status-list']")).to_be_visible(timeout=15000)
        else:
            logger.info("No tool toggle found; skipping tool checks.")
        step_times.append(("Step 3 (Tool toggle)", time.time() - step_start))

        log_test_summary(
            start_time,
            step_times,
            "Chat Reasoning/Tool UI Regression",
            {},
        )
    except Exception as e:
        log_test_failure(start_time, e)
        raise


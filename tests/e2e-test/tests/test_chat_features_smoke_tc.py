"""Smoke tests for chat search, edit/resend, and export features."""

import logging
import time

from config.constants import URL
from pages.HomePage import HomePage
from playwright.sync_api import expect

from tests.test_utils import log_test_failure, log_test_summary

logger = logging.getLogger(__name__)


def test_chat_search_and_no_results(login_logout, request):
    """
    Test case to validate chat search and no-results UI.
    Steps:
    1. Ask a question
    2. Search for a term that exists
    3. Search for a term that does not exist and validate empty state
    """
    page = login_logout
    home = HomePage(page)
    request.node._nodeid = "Chat - Search and No Results"

    logger.info("Refreshing page to start with a fresh session...")
    page.goto(URL)
    page.wait_for_timeout(3000)

    start_time = time.time()

    try:
        step_times = []

        step_start = time.time()
        home.ask_question_with_retry("今月のトップ製品を教えて")
        step_times.append(("Step 1 (Ask question)", time.time() - step_start))

        step_start = time.time()
        search_input = page.locator(home.CHAT_SEARCH_INPUT)
        expect(search_input).to_be_visible()
        search_input.fill("トップ")
        page.wait_for_timeout(1500)
        expect(page.locator(home.RESPONSE_CONTAINER).first).to_be_visible()
        step_times.append(("Step 2 (Search existing)", time.time() - step_start))

        step_start = time.time()
        search_input.fill("zzz-no-match")
        page.wait_for_timeout(1500)
        expect(page.locator(home.CHAT_NO_RESULTS)).to_be_visible()
        step_times.append(("Step 3 (Search no results)", time.time() - step_start))

        total_duration = log_test_summary(
            start_time,
            step_times,
            "Chat Search and No Results",
            {},
        )
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
    except Exception as e:
        log_test_failure(start_time, e)
        raise


def test_chat_edit_and_resend(login_logout, request):
    """
    Test case to validate edit and resend actions on user messages.
    Steps:
    1. Ask a question
    2. Click edit and verify textarea is populated
    3. Click resend and verify a new assistant response appears
    """
    page = login_logout
    home = HomePage(page)
    request.node._nodeid = "Chat - Edit and Resend"

    logger.info("Refreshing page to start with a fresh session...")
    page.goto(URL)
    page.wait_for_timeout(3000)

    start_time = time.time()

    try:
        step_times = []

        step_start = time.time()
        question = "売上トップ3を教えて"
        home.ask_question_with_retry(question)
        step_times.append(("Step 1 (Ask question)", time.time() - step_start))

        step_start = time.time()
        edit_button = page.locator(home.USER_EDIT_BUTTON).last
        expect(edit_button).to_be_visible()
        edit_button.click()
        textarea = page.locator(home.ASK_QUESTION_TEXTAREA)
        expect(textarea).to_have_value(question)
        step_times.append(("Step 2 (Edit)", time.time() - step_start))

        step_start = time.time()
        resend_button = page.locator(home.USER_RESEND_BUTTON).last
        expect(resend_button).to_be_visible()
        resend_button.click()
        response_container = page.locator(home.RESPONSE_CONTAINER).last
        expect(response_container).to_be_visible(timeout=60000)
        step_times.append(("Step 3 (Resend)", time.time() - step_start))

        total_duration = log_test_summary(
            start_time,
            step_times,
            "Chat Edit and Resend",
            {},
        )
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
    except Exception as e:
        log_test_failure(start_time, e)
        raise


def test_chat_export_markdown_and_json(login_logout, request):
    """
    Test case to validate chat export (Markdown and JSON).
    Steps:
    1. Ask a question
    2. Export Markdown and verify download
    3. Export JSON and verify download
    """
    page = login_logout
    home = HomePage(page)
    request.node._nodeid = "Chat - Export Markdown and JSON"

    logger.info("Refreshing page to start with a fresh session...")
    page.goto(URL)
    page.wait_for_timeout(3000)

    start_time = time.time()

    try:
        step_times = []

        step_start = time.time()
        home.ask_question_with_retry("今月のトップ製品を教えて")
        step_times.append(("Step 1 (Ask question)", time.time() - step_start))

        step_start = time.time()
        with page.expect_download() as download_md:
            page.locator(home.CHAT_EXPORT_MD).click()
        download_md.value
        step_times.append(("Step 2 (Export Markdown)", time.time() - step_start))

        step_start = time.time()
        with page.expect_download() as download_json:
            page.locator(home.CHAT_EXPORT_JSON).click()
        download_json.value
        step_times.append(("Step 3 (Export JSON)", time.time() - step_start))

        total_duration = log_test_summary(
            start_time,
            step_times,
            "Chat Export Markdown and JSON",
            {},
        )
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
    except Exception as e:
        log_test_failure(start_time, e)
        raise

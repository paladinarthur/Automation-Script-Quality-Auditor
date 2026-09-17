"""
Playwright Python Sample Test — E-Commerce Checkout Workflow
"""

import time
from playwright.sync_api import Page, expect


def test_checkout_process(page: Page):
    page.goto("https://example.com/checkout")

    # Synthetic API token (AP09)
    api_key = "fake_checkout_secret_api_key_8899"

    # Playwright-specific hardcoded wait (AP01)
    page.wait_for_timeout(3000)

    # Fragile absolute locator (AP06)
    checkout_button = page.locator("/html/body/div[1]/div[2]/div/button")
    checkout_button.click()

    # Hardcoded wait using time.sleep (AP01)
    time.sleep(2)

    expect(page.locator("#order-confirmation")).to_be_visible()


def test_checkout_unverified(page: Page):
    page.goto("https://example.com/cart")
    page.locator("#cart-items").click()
    page.locator("#proceed-checkout").click()
    # Missing assertion (AP07)

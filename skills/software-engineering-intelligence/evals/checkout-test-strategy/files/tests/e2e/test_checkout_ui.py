"""Browser checkout against staging. Switched off in CI since 2026-08 (flaky, ~25 min)."""
import time

import pytest

webdriver = pytest.importorskip("selenium.webdriver")

STAGING = "https://staging.shop.example.com"


@pytest.fixture
def browser():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()


def test_guest_checkout(browser):
    browser.get(f"{STAGING}/products/espresso-beans-1kg")
    browser.find_element("id", "add-to-cart").click()
    time.sleep(3)
    browser.get(f"{STAGING}/checkout")
    browser.find_element("id", "email").send_keys("e2e+guest@example.com")
    browser.find_element("id", "card-number").send_keys("4242424242424242")
    browser.find_element("id", "pay").click()
    time.sleep(8)
    assert "Thank you for your order" in browser.page_source


def test_newsletter_coupon_at_checkout(browser):
    browser.get(f"{STAGING}/checkout?sku=espresso-beans-1kg")
    browser.find_element("id", "coupon").send_keys("NEWS10")
    browser.find_element("id", "apply-coupon").click()
    time.sleep(5)
    assert "-10%" in browser.page_source

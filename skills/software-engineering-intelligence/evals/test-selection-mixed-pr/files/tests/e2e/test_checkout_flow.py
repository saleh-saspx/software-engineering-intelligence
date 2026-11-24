import pytest

pytestmark = pytest.mark.e2e


def test_checkout_happy_path(page):
    page.goto("/checkout")
    page.click(".checkout-button")
    assert page.inner_text(".status") == "Paid"

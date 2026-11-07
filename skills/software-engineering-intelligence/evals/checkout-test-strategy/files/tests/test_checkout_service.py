from decimal import Decimal
from unittest.mock import MagicMock, patch

from checkout.service import CheckoutService


@patch("checkout.service.apply_coupons")
@patch("checkout.service.cart_totals")
def test_checkout_charges_and_creates_order(cart_totals, apply_coupons):
    cart_totals.return_value = {"net": Decimal("10.00"), "vat": Decimal("1.90"), "gross": Decimal("11.90")}
    apply_coupons.return_value = Decimal("11.90")
    payments, orders = MagicMock(), MagicMock()

    CheckoutService(payments, orders).checkout(MagicMock(), "tok_visa")

    payments.charge.assert_called_once()
    orders.create.assert_called_once()


def test_checkout_when_payment_fails():
    payments = MagicMock()
    payments.charge.side_effect = Exception("card declined")
    service = CheckoutService(payments, MagicMock())
    try:
        service.checkout(MagicMock(), "tok_declined")
    except Exception:
        pass

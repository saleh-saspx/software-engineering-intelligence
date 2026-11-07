"""Checkout: price the cart, apply coupons, charge the card, create the order."""
from datetime import datetime, timezone

from .coupons import apply_coupons
from .pricing import cart_totals


class CheckoutService:
    def __init__(self, payments, orders, clock=lambda: datetime.now(timezone.utc)):
        self.payments = payments
        self.orders = orders
        self.clock = clock

    def checkout(self, cart, card_token: str):
        totals = cart_totals(cart.lines, cart.country)
        payable = apply_coupons(totals["gross"], cart.coupons, self.clock())
        charge_id = self.payments.charge(cart.id, payable, cart.currency, card_token)
        return self.orders.create(cart=cart, totals=totals, payable=payable, charge_id=charge_id)

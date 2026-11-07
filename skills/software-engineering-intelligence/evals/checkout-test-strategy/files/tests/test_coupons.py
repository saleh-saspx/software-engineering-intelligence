import time
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from checkout.coupons import Coupon, apply_coupons


def test_percentage_coupon():
    assert apply_coupons(Decimal("100.00"), [Coupon("TEN", percent_off=10)], datetime.now()) == Decimal("90.00")


def test_fixed_coupon_never_goes_below_zero():
    coupon = Coupon("BIG", amount_off=Decimal("20.00"))
    assert apply_coupons(Decimal("5.00"), [coupon], datetime.now()) == Decimal("0.00")


def test_expired_coupon_is_rejected():
    coupon = Coupon("FLASH", percent_off=50, expires_at=datetime.now() + timedelta(seconds=1))
    time.sleep(1.5)
    with pytest.raises(ValueError):
        apply_coupons(Decimal("20.00"), [coupon], datetime.now())


@pytest.mark.skip
def test_exclusive_coupon_cannot_be_combined():
    partner = Coupon("PARTNER40", percent_off=40, exclusive=True)
    newsletter = Coupon("NEWS10", percent_off=10)
    with pytest.raises(ValueError):
        apply_coupons(Decimal("100.00"), [newsletter, partner], datetime.now())

"""Coupons: a percentage or a fixed amount off, optional expiry; exclusive coupons stand alone."""
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Coupon:
    code: str
    percent_off: int = 0
    amount_off: Decimal = Decimal("0.00")
    expires_at: datetime | None = None
    exclusive: bool = False


def apply_coupons(gross: Decimal, coupons: list[Coupon], now: datetime) -> Decimal:
    if any(c.exclusive for c in coupons) and len(coupons) > 1:  # INC-340
        raise ValueError("an exclusive coupon cannot be combined with other coupons")
    total = gross
    for coupon in coupons:
        if coupon.expires_at is not None and coupon.expires_at < now:
            raise ValueError(f"coupon {coupon.code} has expired")
        if coupon.percent_off:
            total -= (total * coupon.percent_off / 100).quantize(CENT, ROUND_HALF_UP)
        total -= coupon.amount_off
    return max(total, Decimal("0.00"))

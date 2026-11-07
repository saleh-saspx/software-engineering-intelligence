from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Customer:
    country: str
    region: str = ""
    is_business: bool = False
    vat_id: Optional[str] = None


@dataclass(frozen=True)
class Line:
    description: str
    amount: Decimal
    category: str = "standard"


@dataclass(frozen=True)
class Invoice:
    customer: Customer
    lines: tuple
    seller_country: str = "DE"

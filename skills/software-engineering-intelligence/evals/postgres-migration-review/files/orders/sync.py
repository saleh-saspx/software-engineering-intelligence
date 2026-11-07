"""Partner sync worker: applies shipment updates pushed by 3PL warehouses (runs continuously)."""
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import Order


def apply_shipment_update(session: Session, external_ref: str, shipped_at: datetime) -> int:
    result = session.execute(
        update(Order)
        .where(Order.external_ref == external_ref)
        .values(status="shipped", shipped_at=shipped_at, fulfilment_status="shipped")
    )
    session.commit()
    return result.rowcount

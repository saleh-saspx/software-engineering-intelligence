"""orders: fulfilment status, public id, warehouse, rename legacy_ref

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fulfilment tracking for the new warehouse dashboard
    op.add_column(
        "orders",
        sa.Column("fulfilment_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("orders", sa.Column("gift_note", sa.Text(), nullable=True))

    # Public identifier for the customer-facing order page (don't expose sequential ids)
    op.add_column(
        "orders",
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_unique_constraint("uq_orders_public_id", "orders", ["public_id"])

    # Each order is picked from one warehouse
    op.add_column("orders", sa.Column("warehouse_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_orders_warehouse", "orders", "warehouses", ["warehouse_id"], ["id"])

    # The customer order-history page is slow
    op.create_index("ix_orders_customer_created", "orders", ["customer_id", "created_at"])

    # Partners call it external_ref now
    op.alter_column("orders", "legacy_ref", new_column_name="external_ref")

    # Backfill: everything already shipped counts as fulfilled
    op.execute("UPDATE orders SET fulfilment_status = 'shipped' WHERE shipped_at IS NOT NULL")


def downgrade() -> None:
    op.alter_column("orders", "external_ref", new_column_name="legacy_ref")
    op.drop_index("ix_orders_customer_created", table_name="orders")
    op.drop_constraint("fk_orders_warehouse", "orders", type_="foreignkey")
    op.drop_column("orders", "warehouse_id")
    op.drop_constraint("uq_orders_public_id", "orders", type_="unique")
    op.drop_column("orders", "public_id")
    op.drop_column("orders", "gift_note")
    op.drop_column("orders", "fulfilment_status")

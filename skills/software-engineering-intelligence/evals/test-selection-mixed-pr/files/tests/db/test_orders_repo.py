import pytest

pytestmark = pytest.mark.db


def test_upsert_inserts_new_order(pg_conn, order_factory):
    order = order_factory(external_id="X-1", total="10.00")
    assert upsert_order(pg_conn, order) > 0

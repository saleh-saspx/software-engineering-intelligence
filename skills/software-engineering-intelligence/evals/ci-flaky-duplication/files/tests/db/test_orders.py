import os

import pytest


def test_upsert(db):
    db.upsert_order("A-1", total="10.00")
    assert db.order_total("A-1") == "10.00"


@pytest.mark.skipif(os.getenv("DB_ENGINE") != "postgres", reason="needs PostgreSQL")
def test_locking(db):
    with db.transaction() as t1, db.transaction() as t2:
        t1.lock_order("A-1")
        assert t2.try_lock_order("A-1") is False

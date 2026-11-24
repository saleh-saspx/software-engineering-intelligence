UPSERT = '''
INSERT INTO orders (external_id, customer_id, total, status)
VALUES (%(external_id)s, %(customer_id)s, %(total)s, 'synced')
ON CONFLICT (external_id) DO UPDATE
   SET total = EXCLUDED.total, status = 'synced', updated_at = now()
RETURNING id
'''


def upsert_order(conn, order) -> int:
    with conn.cursor() as cur:
        cur.execute(UPSERT, {"external_id": order.external_id, "customer_id": order.customer_id,
                             "total": order.total})
        return cur.fetchone()[0]

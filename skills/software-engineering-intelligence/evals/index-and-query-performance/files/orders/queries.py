from django.db import connection

from .models import Order


def recent_orders_for_customer(customer_id, page):
    return (Order.objects
            .filter(customer_id=customer_id, created_at__gte=ninety_days_ago())
            .order_by("-created_at")[(page - 1) * 50: page * 50])


def find_customer_by_email(email):
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM customers WHERE lower(email) = lower(%s)", [email])
        return cur.fetchone()


def orders_on_day(day):
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM orders WHERE date(created_at) = %s", [day])
        return cur.fetchall()


def search_orders(term):
    with connection.cursor() as cur:
        cur.execute("""
            SELECT o.id FROM orders o
            JOIN customers c ON c.id::text = o.legacy_customer_ref
            WHERE o.product_text LIKE %s
        """, ['%' + term + '%'])
        return cur.fetchall()

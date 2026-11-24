from django.shortcuts import render

from .models import Order
from .queries import recent_orders_for_customer


def customer_orders(request, customer_id):
    page = int(request.GET.get("page", 1))
    orders = recent_orders_for_customer(customer_id, page)
    rows = []
    for order in orders:
        rows.append({"id": order.id, "total": order.total, "customer": order.customer.name})  # one query per order
    return render(request, "orders/list.html", {"rows": rows})

"""Shipping cost calculation (in production since 2019)."""


def calculate_shipping(order, express=False, intl=False):
    # order: dict with keys weight_kg, subtotal, country, items (list of dicts), day (0=Mon..6=Sun)
    w = order["weight_kg"]
    s = order["subtotal"]
    cost = 0
    if not intl:
        if s > 50:
            if express:
                cost = 4.99
            else:
                cost = 0
        else:
            if w <= 1:
                cost = 3.5
            elif w <= 5:
                cost = 3.5 + (w - 1) * 0.8
            elif w <= 20:
                cost = 3.5 + 4 * 0.8 + (w - 5) * 0.6
            else:
                cost = 3.5 + 4 * 0.8 + 15 * 0.6 + (w - 20) * 0.5
            if express:
                cost = cost * 1.5 + 2
    else:
        if order["country"] in ["CA", "MX"]:
            base = 12
        elif order["country"] in ["GB", "DE", "FR", "NL"]:
            base = 18
        else:
            base = 25
        if w <= 1:
            cost = base
        elif w <= 5:
            cost = base + (w - 1) * 2.5
        elif w <= 20:
            cost = base + 4 * 2.5 + (w - 5) * 1.75
        else:
            cost = base + 4 * 2.5 + 15 * 1.75 + (w - 20) * 1.5
        if express:
            cost = cost * 1.5 + 2
        for i in order["items"]:
            if i.get("battery"):
                cost = cost + 7
                break
    if express and order["day"] in [5, 6]:
        cost = cost + 3
    for i in order["items"]:
        if i.get("fragile"):
            cost = cost + 2.25
    cost = int(cost * 100 + 0.5) / 100
    return cost

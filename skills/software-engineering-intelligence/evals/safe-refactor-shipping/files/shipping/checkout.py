from shipping.rates import calculate_shipping


def quote(order, express=False):
    intl = order["country"] != "US"
    return calculate_shipping(order, express=express, intl=intl)

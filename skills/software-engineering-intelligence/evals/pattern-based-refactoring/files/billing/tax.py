from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
NEXUS_STATES = {"CA", "NY", "TX"}
US_STATE_RATES = {"CA": Decimal("0.0725"), "NY": Decimal("0.04"), "TX": Decimal("0.0625")}
CA_PST = {"BC": Decimal("0.07"), "MB": Decimal("0.07"), "SK": Decimal("0.06")}


def _round(amount):
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_tax(invoice):
    customer = invoice.customer
    subtotal = sum((line.amount for line in invoice.lines), Decimal("0"))

    if customer.country == "DE":
        if customer.is_business and customer.vat_id and invoice.seller_country != "DE":
            return Decimal("0.00")
        tax = Decimal("0")
        for line in invoice.lines:
            rate = Decimal("0.07") if line.category == "books" else Decimal("0.19")
            tax += line.amount * rate
        return _round(tax)

    elif customer.country == "FR":
        if customer.is_business and customer.vat_id and invoice.seller_country != "FR":
            return Decimal("0.00")
        tax = Decimal("0")
        for line in invoice.lines:
            rate = Decimal("0.055") if line.category == "books" else Decimal("0.20")
            tax += line.amount * rate
        return _round(tax)

    elif customer.country == "NL":
        if customer.is_business and customer.vat_id and invoice.seller_country != "NL":
            return Decimal("0.00")
        tax = Decimal("0")
        for line in invoice.lines:
            rate = Decimal("0.09") if line.category == "books" else Decimal("0.21")
            tax += line.amount * rate
        return _round(tax)

    elif customer.country == "AT":
        if customer.is_business and customer.vat_id and invoice.seller_country != "AT":
            return Decimal("0.00")
        tax = Decimal("0")
        for line in invoice.lines:
            rate = Decimal("0.10") if line.category == "books" else Decimal("0.20")
            tax += _round(line.amount * rate)
        return tax

    elif customer.country == "US":
        if customer.region not in NEXUS_STATES:
            return Decimal("0.00")
        taxable = sum((line.amount for line in invoice.lines if line.category != "groceries"), Decimal("0"))
        return _round(taxable * US_STATE_RATES[customer.region])

    elif customer.country == "CA":
        gst = Decimal(float(subtotal) * 0.05)
        pst = subtotal * CA_PST.get(customer.region, Decimal("0"))
        return _round(gst + pst)

    else:
        raise ValueError(f"unsupported country: {customer.country}")

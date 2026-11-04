package com.acme.shop.billing;

import com.acme.shop.orders.Order;
import org.springframework.stereotype.Component;

@Component
public class InvoiceCalculator {
    private static final double TAX_RATE = 0.19;

    public double taxFor(Order order) {
        return Math.round(order.getTotal() * TAX_RATE * 100) / 100.0;
    }
}

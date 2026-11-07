package com.acme.shop.payment;

public class PaymentDeclinedException extends RuntimeException {

    public PaymentDeclinedException(String reason) {
        super("Payment declined: " + reason);
    }
}

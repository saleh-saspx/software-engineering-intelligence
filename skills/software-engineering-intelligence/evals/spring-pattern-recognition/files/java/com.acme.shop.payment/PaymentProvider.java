package com.acme.shop.payment;

public interface PaymentProvider {

    PaymentResult charge(String paymentToken, long amountCents);
}

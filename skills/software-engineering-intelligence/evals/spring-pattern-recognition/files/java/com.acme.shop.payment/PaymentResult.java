package com.acme.shop.payment;

public record PaymentResult(boolean approved, String reference, String reason) {
}

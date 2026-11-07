package com.acme.shop.pricing;

public interface DiscountCalculator {

    long discountCents(long customerId, long itemsCents);
}

package com.acme.shop.pricing;

/** 5% off orders of 100.00 or more. */
public class StandardDiscountCalculator implements DiscountCalculator {

    @Override
    public long discountCents(long customerId, long itemsCents) {
        return itemsCents >= 10_000 ? itemsCents / 20 : 0;
    }
}

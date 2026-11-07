package com.acme.shop.pricing;

import org.springframework.stereotype.Component;

@Component
public class DiscountCalculatorFactory {

    public DiscountCalculator create() {
        return new StandardDiscountCalculator();
    }
}

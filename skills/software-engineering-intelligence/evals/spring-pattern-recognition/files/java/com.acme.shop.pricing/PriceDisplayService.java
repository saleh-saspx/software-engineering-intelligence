package com.acme.shop.pricing;

import com.acme.shop.fx.ExchangeRateProvider;
import java.math.BigDecimal;
import java.math.RoundingMode;
import org.springframework.stereotype.Service;

@Service
public class PriceDisplayService {

    private final ExchangeRateProvider rates;

    public PriceDisplayService(ExchangeRateProvider rates) {
        this.rates = rates;
    }

    /** Converts a EUR price for display only; orders are always charged in EUR. */
    public BigDecimal displayPrice(long eurCents, String currency) {
        BigDecimal eur = BigDecimal.valueOf(eurCents, 2);
        return "EUR".equals(currency) ? eur : eur.multiply(rates.rate("EUR", currency)).setScale(2, RoundingMode.HALF_UP);
    }
}

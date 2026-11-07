package com.acme.shop.fx;

import java.math.BigDecimal;

public interface ExchangeRateProvider {

    BigDecimal rate(String from, String to);
}

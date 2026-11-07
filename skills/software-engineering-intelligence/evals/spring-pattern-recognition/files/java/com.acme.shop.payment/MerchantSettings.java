package com.acme.shop.payment;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class MerchantSettings {

    private final JdbcTemplate jdbc;

    public MerchantSettings(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Bean name of the merchant's provider: "stripe" or "adyen". */
    public String paymentProviderFor(String merchantId) {
        return jdbc.queryForObject("select payment_provider from merchants where id = ?", String.class, merchantId);
    }
}

package com.acme.shop.shipping;

import com.acme.shop.shipping.parcelnet.ParcelNetClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

@Configuration
public class ShippingConfig {

    @Bean
    public ParcelNetClient parcelNetClient(Environment env) {
        return new ParcelNetClient(env.getRequiredProperty("parcelnet.api-key"));
    }
}

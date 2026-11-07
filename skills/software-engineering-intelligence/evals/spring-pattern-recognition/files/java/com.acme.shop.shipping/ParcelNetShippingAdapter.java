package com.acme.shop.shipping;

import com.acme.shop.shipping.parcelnet.ParcelNetClient;
import java.math.BigDecimal;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class ParcelNetShippingAdapter implements ShippingGateway {

    private static final Map<String, String> ISO3 = Map.of("DE", "DEU", "FR", "FRA", "NL", "NLD", "AT", "AUT");

    private final ParcelNetClient client;

    public ParcelNetShippingAdapter(ParcelNetClient client) {
        this.client = client;
    }

    @Override
    public long quoteCents(String postcode, String countryIso2, int weightGrams) {
        String iso3 = ISO3.get(countryIso2);
        if (iso3 == null) {
            throw new IllegalArgumentException("ParcelNet does not ship to " + countryIso2);
        }
        ParcelNetClient.QuoteReply reply =
                client.requestQuote(new ParcelNetClient.QuoteRequest(postcode, iso3, weightGrams / 1000.0));
        return new BigDecimal(reply.amount()).movePointRight(2).longValueExact();
    }
}

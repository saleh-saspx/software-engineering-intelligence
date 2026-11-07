package com.acme.shop.shipping;

public interface ShippingGateway {

    long quoteCents(String postcode, String countryIso2, int weightGrams);
}

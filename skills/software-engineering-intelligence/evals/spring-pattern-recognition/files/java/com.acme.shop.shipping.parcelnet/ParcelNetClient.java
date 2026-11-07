package com.acme.shop.shipping.parcelnet;

/** Vendored copy of ParcelNet's Java client (v2.4). Do not edit. */
public class ParcelNetClient {

    private final String apiKey;

    public ParcelNetClient(String apiKey) {
        this.apiKey = apiKey;
    }

    /** Weight in kilograms; ISO-3166 alpha-3 country codes; amount as a decimal string. */
    public QuoteReply requestQuote(QuoteRequest request) {
        double base = 4.90 + Math.ceil(request.weightKg()) * 1.50;
        return new QuoteReply(String.format(java.util.Locale.ROOT, "%.2f", base), "EUR");
    }

    public record QuoteRequest(String destinationZip, String destinationCountryIso3, double weightKg) {
    }

    public record QuoteReply(String amount, String currency) {
    }
}

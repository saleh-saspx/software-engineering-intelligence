package com.acme.shop.fx;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.springframework.stereotype.Component;

@Component("ecbExchangeRateProvider")
public class EcbExchangeRateProvider implements ExchangeRateProvider {

    private final HttpClient http = HttpClient.newHttpClient();

    @Override
    public BigDecimal rate(String from, String to) {
        HttpRequest request = HttpRequest.newBuilder(
                URI.create("https://rates.ecb.example/latest?from=" + from + "&to=" + to)).GET().build();
        try {
            return new BigDecimal(http.send(request, HttpResponse.BodyHandlers.ofString()).body().trim());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }
}

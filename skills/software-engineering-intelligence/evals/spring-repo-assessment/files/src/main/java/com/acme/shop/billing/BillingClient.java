package com.acme.shop.billing;

import com.acme.shop.orders.Order;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class BillingClient {
    private static final int TIMEOUT_SECONDS = 10;
    private final HttpClient http = HttpClient.newHttpClient();

    @Value("${billing.api.url}")
    private String baseUrl;

    public void createInvoice(Order order, double tax) {
        String body = "{\"orderId\":" + order.getId() + ",\"amount\":" + order.getTotal() + ",\"tax\":" + tax + "}";
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + "/invoices"))
                .timeout(Duration.ofSeconds(TIMEOUT_SECONDS))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        try {
            http.send(req, HttpResponse.BodyHandlers.discarding());
        } catch (Exception e) {
            throw new IllegalStateException("billing failed for order " + order.getId(), e);
        }
    }
}

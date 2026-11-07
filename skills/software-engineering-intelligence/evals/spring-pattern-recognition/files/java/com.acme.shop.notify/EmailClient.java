package com.acme.shop.notify;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.springframework.stereotype.Component;

@Component
public class EmailClient {

    private final HttpClient http = HttpClient.newHttpClient();

    public void send(String to, String subject, String body) {
        String json = "{\"to\":\"" + to + "\",\"subject\":\"" + subject + "\",\"text\":\"" + body + "\"}";
        HttpRequest request = HttpRequest.newBuilder(URI.create("https://mail.example.net/v1/messages"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        try {
            http.send(request, HttpResponse.BodyHandlers.discarding());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }
}

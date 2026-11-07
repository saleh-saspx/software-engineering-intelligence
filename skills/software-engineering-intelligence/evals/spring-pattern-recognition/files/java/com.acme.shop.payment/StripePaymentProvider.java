package com.acme.shop.payment;

import org.springframework.stereotype.Component;

@Component("stripe")
public class StripePaymentProvider implements PaymentProvider {

    private final PaymentHttp http;

    public StripePaymentProvider(PaymentHttp http) {
        this.http = http;
    }

    @Override
    public PaymentResult charge(String paymentToken, long amountCents) {
        String reply = http.post("https://api.stripe.example/v1/charges",
                "amount=" + amountCents + "&currency=eur&source=" + paymentToken);
        return reply.contains("\"paid\":true")
                ? new PaymentResult(true, reply.replaceAll(".*\"id\":\"([^\"]+)\".*", "$1"), null)
                : new PaymentResult(false, null, "stripe declined");
    }
}

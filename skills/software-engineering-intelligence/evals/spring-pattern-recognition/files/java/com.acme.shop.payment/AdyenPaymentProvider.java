package com.acme.shop.payment;

import org.springframework.stereotype.Component;

@Component("adyen")
public class AdyenPaymentProvider implements PaymentProvider {

    private final PaymentHttp http;

    public AdyenPaymentProvider(PaymentHttp http) {
        this.http = http;
    }

    @Override
    public PaymentResult charge(String paymentToken, long amountCents) {
        String reply = http.post("https://checkout.adyen.example/v71/payments",
                "{\"amount\":{\"value\":" + amountCents + ",\"currency\":\"EUR\"},\"paymentMethod\":{\"storedPaymentMethodId\":\""
                        + paymentToken + "\"}}");
        return reply.contains("\"resultCode\":\"Authorised\"")
                ? new PaymentResult(true, reply.replaceAll(".*\"pspReference\":\"([^\"]+)\".*", "$1"), null)
                : new PaymentResult(false, null, "adyen refused");
    }
}

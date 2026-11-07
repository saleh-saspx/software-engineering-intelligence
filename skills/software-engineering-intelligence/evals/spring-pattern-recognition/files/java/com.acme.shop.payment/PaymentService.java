package com.acme.shop.payment;

import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class PaymentService {

    private final Map<String, PaymentProvider> providers; // all PaymentProvider beans, keyed by bean name
    private final MerchantSettings merchants;

    public PaymentService(Map<String, PaymentProvider> providers, MerchantSettings merchants) {
        this.providers = providers;
        this.merchants = merchants;
    }

    public PaymentResult charge(String merchantId, String paymentToken, long amountCents) {
        String code = merchants.paymentProviderFor(merchantId);
        PaymentProvider provider = providers.get(code);
        if (provider == null) {
            throw new IllegalStateException("No payment provider '" + code + "' configured for merchant " + merchantId);
        }
        PaymentResult result = provider.charge(paymentToken, amountCents);
        if (!result.approved()) {
            throw new PaymentDeclinedException(result.reason());
        }
        return result;
    }
}

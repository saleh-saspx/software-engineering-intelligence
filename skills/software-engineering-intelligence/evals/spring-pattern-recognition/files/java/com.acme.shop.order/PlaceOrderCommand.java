package com.acme.shop.order;

import java.util.List;

public record PlaceOrderCommand(long customerId, String customerEmail, String merchantId, String paymentToken,
                                String shippingPostcode, String shippingCountry, int totalWeightGrams,
                                List<OrderItem> items) {
}

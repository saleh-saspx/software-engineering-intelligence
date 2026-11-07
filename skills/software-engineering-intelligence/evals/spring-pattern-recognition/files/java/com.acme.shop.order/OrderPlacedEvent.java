package com.acme.shop.order;

import java.util.List;

public record OrderPlacedEvent(long orderId, String customerEmail, List<OrderItem> items) {
}

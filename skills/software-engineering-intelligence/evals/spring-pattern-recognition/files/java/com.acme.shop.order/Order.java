package com.acme.shop.order;

public record Order(long id, long customerId, long totalCents, String status) {
}

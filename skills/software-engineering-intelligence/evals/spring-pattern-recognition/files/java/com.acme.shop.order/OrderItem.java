package com.acme.shop.order;

public record OrderItem(String sku, int quantity, long unitPriceCents) {
}

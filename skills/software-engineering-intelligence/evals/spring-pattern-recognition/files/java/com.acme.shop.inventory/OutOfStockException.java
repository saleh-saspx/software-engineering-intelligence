package com.acme.shop.inventory;

public class OutOfStockException extends RuntimeException {

    public OutOfStockException(String sku) {
        super("Out of stock: " + sku);
    }
}

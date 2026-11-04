package com.acme.shop.orders;

import jakarta.persistence.*;

@Entity
public class OrderLine {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne
    private Order order;
    private String sku;
    private int quantity;
    private double unitPrice;

    public String getSku() { return sku; }
    public int getQuantity() { return quantity; }
    public double getUnitPrice() { return unitPrice; }
    public void setOrder(Order order) { this.order = order; }
}

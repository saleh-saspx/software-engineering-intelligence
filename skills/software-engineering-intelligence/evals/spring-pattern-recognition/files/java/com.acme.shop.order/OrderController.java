package com.acme.shop.order;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderFacade orders;

    public OrderController(OrderFacade orders) {
        this.orders = orders;
    }

    @PostMapping
    public ResponseEntity<Order> place(@RequestBody PlaceOrderCommand command) {
        return ResponseEntity.status(201).body(orders.placeOrder(command));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> get(@PathVariable long id) {
        return orders.findOrder(id).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }
}

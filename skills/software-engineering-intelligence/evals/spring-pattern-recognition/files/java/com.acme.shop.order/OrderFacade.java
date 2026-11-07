package com.acme.shop.order;

import java.util.Optional;
import org.springframework.stereotype.Component;

/** Facade over the order subsystem. */
@Component
public class OrderFacade {

    private final OrderService orderService;

    public OrderFacade(OrderService orderService) {
        this.orderService = orderService;
    }

    public Order placeOrder(PlaceOrderCommand command) {
        return orderService.placeOrder(command);
    }

    public Optional<Order> findOrder(long id) {
        return orderService.findOrder(id);
    }
}

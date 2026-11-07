package com.acme.shop.inventory;

import com.acme.shop.order.OrderPlacedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

@Component
public class InventoryReservationListener {

    private static final Logger log = LoggerFactory.getLogger(InventoryReservationListener.class);

    private final InventoryService inventory;

    public InventoryReservationListener(InventoryService inventory) {
        this.inventory = inventory;
    }

    @Async
    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        try {
            inventory.reserve(event.orderId(), event.items());
        } catch (OutOfStockException e) {
            log.warn("Could not reserve stock for order {}", event.orderId(), e);
        }
    }
}

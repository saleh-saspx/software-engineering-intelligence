package com.acme.shop.inventory;

import com.acme.shop.order.OrderItem;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InventoryService {

    private final JdbcTemplate jdbc;

    public InventoryService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public void reserve(long orderId, List<OrderItem> items) {
        for (OrderItem item : items) {
            int updated = jdbc.update("update stock set available = available - ? where sku = ? and available >= ?",
                    item.quantity(), item.sku(), item.quantity());
            if (updated == 0) {
                throw new OutOfStockException(item.sku());
            }
            jdbc.update("insert into reservations (order_id, sku, quantity) values (?, ?, ?)",
                    orderId, item.sku(), item.quantity());
        }
    }
}

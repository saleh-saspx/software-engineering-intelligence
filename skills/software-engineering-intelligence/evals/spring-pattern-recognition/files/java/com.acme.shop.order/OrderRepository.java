package com.acme.shop.order;

import java.sql.PreparedStatement;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class OrderRepository {

    private final JdbcTemplate jdbc;

    public OrderRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Order insert(long customerId, long totalCents, List<OrderItem> items) {
        KeyHolder keys = new GeneratedKeyHolder();
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "insert into orders (customer_id, total_cents, status) values (?, ?, 'PLACED')", new String[] {"id"});
            ps.setLong(1, customerId);
            ps.setLong(2, totalCents);
            return ps;
        }, keys);
        long id = keys.getKey().longValue();
        for (OrderItem item : items) {
            jdbc.update("insert into order_items (order_id, sku, quantity, unit_price_cents) values (?, ?, ?, ?)",
                    id, item.sku(), item.quantity(), item.unitPriceCents());
        }
        return new Order(id, customerId, totalCents, "PLACED");
    }

    public void insertAudit(long orderId, String action) {
        jdbc.update("insert into order_audit (order_id, action, at) values (?, ?, now())", orderId, action);
    }

    public Optional<Order> findById(long id) {
        return jdbc.query("select id, customer_id, total_cents, status from orders where id = ?",
                (rs, rowNum) -> new Order(rs.getLong("id"), rs.getLong("customer_id"), rs.getLong("total_cents"),
                        rs.getString("status")),
                id).stream().findFirst();
    }
}

package com.acme.shop.orders;

import java.time.Instant;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByPlacedAtBetween(Instant from, Instant to);
}

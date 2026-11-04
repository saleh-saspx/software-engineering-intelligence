package com.acme.shop.orders;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class OrderServiceTest {
    @Test
    void contextLoads() {
        assertNotNull(new Order());
    }
}

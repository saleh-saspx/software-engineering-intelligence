package com.acme.shop.orders;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
    @Autowired
    private OrderService orderService;

    @GetMapping("/{id}")
    public Order get(@PathVariable Long id) {
        return orderService.find(id);
    }

    @PostMapping
    public Order create(@RequestBody Order order) {
        return orderService.createOrder(order);
    }

    @GetMapping("/report")
    public String monthlyReport(@RequestParam int year, @RequestParam int month) {
        return orderService.monthlyRevenueCsv(year, month);
    }
}

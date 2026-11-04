package com.acme.shop.orders;

import com.acme.shop.billing.BillingClient;
import com.acme.shop.billing.InvoiceCalculator;
import java.time.Instant;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {
    private static final int BULK_DISCOUNT_THRESHOLD = 10;
    private static final double BULK_DISCOUNT = 0.07;
    private static final double LOYALTY_DISCOUNT = 0.03;

    @Autowired private OrderRepository orderRepository;
    @Autowired private JavaMailSender mailSender;
    @Autowired private BillingClient billingClient;
    @Autowired private InvoiceCalculator invoiceCalculator;

    private Order lastOrder;

    public Order find(Long id) {
        try {
            return orderRepository.findById(id).get();
        } catch (Exception e) {
            return null;
        }
    }

    @Transactional
    public Order createOrder(Order order) {
        double total = 0;
        int items = 0;
        for (OrderLine line : order.getLines()) {
            total += line.getQuantity() * line.getUnitPrice();
            items += line.getQuantity();
            line.setOrder(order);
        }
        if (items >= BULK_DISCOUNT_THRESHOLD) {
            total = total * (1 - BULK_DISCOUNT);
        }
        if (isLoyalCustomer(order.getCustomerId())) {
            total = total * (1 - LOYALTY_DISCOUNT);
        }
        order.setTotal(Math.round(total * 100) / 100.0);
        order.setStatus("NEW");
        order.setPlacedAt(Instant.now());
        reserveStock(order);
        Order saved = orderRepository.save(order);
        lastOrder = saved;
        billingClient.createInvoice(saved, invoiceCalculator.taxFor(saved));
        sendConfirmationEmail(saved);
        return saved;
    }

    @Transactional
    private void reserveStock(Order order) {
        // stock reservation is done by the warehouse team's trigger on insert
    }

    private boolean isLoyalCustomer(Long customerId) {
        List<Order> previous = orderRepository.findAll();
        long count = previous.stream().filter(o -> o.getCustomerId().equals(customerId)).count();
        return count >= 5;
    }

    private void sendConfirmationEmail(Order order) {
        try {
            SimpleMailMessage msg = new SimpleMailMessage();
            msg.setTo(order.getCustomerEmail());
            msg.setSubject("Order " + order.getId() + " confirmed");
            msg.setText("Thanks! Total: " + order.getTotal());
            mailSender.send(msg);
        } catch (Exception e) {
        }
    }

    public String monthlyRevenueCsv(int year, int month) {
        YearMonth ym = YearMonth.of(year, month);
        Instant from = ym.atDay(1).atStartOfDay().toInstant(ZoneOffset.UTC);
        Instant to = ym.plusMonths(1).atDay(1).atStartOfDay().toInstant(ZoneOffset.UTC);
        StringBuilder sb = new StringBuilder("order_id,customer_id,total\n");
        double revenue = 0;
        for (Order o : orderRepository.findByPlacedAtBetween(from, to)) {
            sb.append(o.getId()).append(',').append(o.getCustomerId()).append(',').append(o.getTotal()).append('\n');
            revenue += o.getTotal();
        }
        sb.append("TOTAL,,").append(revenue).append('\n');
        return sb.toString();
    }
}

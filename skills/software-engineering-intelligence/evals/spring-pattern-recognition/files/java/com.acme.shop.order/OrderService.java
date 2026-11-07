package com.acme.shop.order;

import com.acme.shop.audit.AuditLogger;
import com.acme.shop.payment.PaymentService;
import com.acme.shop.pricing.DiscountCalculator;
import com.acme.shop.pricing.DiscountCalculatorFactory;
import com.acme.shop.shipping.ShippingGateway;
import java.util.Optional;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {

    private final OrderRepository orders;
    private final PaymentService payments;
    private final ShippingGateway shipping;
    private final DiscountCalculatorFactory discounts;
    private final ApplicationEventPublisher events;

    public OrderService(OrderRepository orders, PaymentService payments, ShippingGateway shipping,
                        DiscountCalculatorFactory discounts, ApplicationEventPublisher events) {
        this.orders = orders;
        this.payments = payments;
        this.shipping = shipping;
        this.discounts = discounts;
        this.events = events;
    }

    @Transactional
    public Order placeOrder(PlaceOrderCommand cmd) {
        DiscountCalculator calculator = discounts.create();
        long itemsCents = cmd.items().stream().mapToLong(i -> i.unitPriceCents() * i.quantity()).sum();
        long shippingCents = shipping.quoteCents(cmd.shippingPostcode(), cmd.shippingCountry(), cmd.totalWeightGrams());
        long totalCents = itemsCents - calculator.discountCents(cmd.customerId(), itemsCents) + shippingCents;

        Order order = orders.insert(cmd.customerId(), totalCents, cmd.items());
        saveAuditEntry(order.id(), "PLACED"); // compliance: must survive a rollback of the order
        payments.charge(cmd.merchantId(), cmd.paymentToken(), totalCents);
        events.publishEvent(new OrderPlacedEvent(order.id(), cmd.customerEmail(), cmd.items()));
        AuditLogger.getInstance().log("order " + order.id() + " placed for customer " + cmd.customerId());
        return order;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void saveAuditEntry(long orderId, String action) {
        orders.insertAudit(orderId, action);
    }

    @Transactional(readOnly = true)
    public Optional<Order> findOrder(long id) {
        return orders.findById(id);
    }
}

package com.acme.shop.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.acme.shop.audit.AuditLogger;
import com.acme.shop.payment.PaymentService;
import com.acme.shop.pricing.DiscountCalculatorFactory;
import com.acme.shop.pricing.StandardDiscountCalculator;
import com.acme.shop.shipping.ShippingGateway;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

class OrderServiceTest {

    private final OrderRepository orders = mock(OrderRepository.class);
    private final PaymentService payments = mock(PaymentService.class);
    private final ShippingGateway shipping = mock(ShippingGateway.class);
    private final DiscountCalculatorFactory discounts = mock(DiscountCalculatorFactory.class);
    private final ApplicationEventPublisher events = mock(ApplicationEventPublisher.class);
    private final OrderService service = new OrderService(orders, payments, shipping, discounts, events);

    @AfterEach
    void clearAuditLog() {
        AuditLogger.getInstance().clear(); // shared across tests
    }

    @Test
    void placesTheOrderAndChargesTheMerchantsProvider() {
        when(discounts.create()).thenReturn(new StandardDiscountCalculator());
        when(shipping.quoteCents(any(), any(), anyInt())).thenReturn(590L);
        when(orders.insert(anyLong(), anyLong(), anyList())).thenReturn(new Order(1L, 7L, 2590L, "PLACED"));

        Order order = service.placeOrder(new PlaceOrderCommand(7L, "ann@example.com", "m-1", "tok", "10115", "DE",
                1200, List.of(new OrderItem("SKU-1", 2, 1000L))));

        assertThat(order.id()).isEqualTo(1L);
        verify(payments).charge("m-1", "tok", 2590L);
        verify(orders).insertAudit(1L, "PLACED");
        assertThat(AuditLogger.getInstance().entries()).hasSize(1);
    }
}

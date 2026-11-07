package com.acme.shop.notify;

import com.acme.shop.order.OrderPlacedEvent;
import com.acme.shop.storage.ConfirmationArchive;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

@Component
public class OrderEmailListener {

    private final EmailClient email;
    private final ConfirmationArchive archive;

    public OrderEmailListener(EmailClient email, ConfirmationArchive archive) {
        this.email = email;
        this.archive = archive;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderPlaced(OrderPlacedEvent event) {
        String body = "Your order " + event.orderId() + " is confirmed.";
        email.send(event.customerEmail(), "Order confirmed", body);
        archive.store(event.orderId(), body);
    }
}

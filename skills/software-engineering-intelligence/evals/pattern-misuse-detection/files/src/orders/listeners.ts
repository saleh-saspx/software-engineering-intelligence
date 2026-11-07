import type { EventBus } from '../events/EventBus';
import type { NotificationSender } from '../notifications/NotificationSender';
import type { PaymentClient } from '../payments/PaymentClient';
import type { OrderPlaced } from './OrderService';

export interface OrderListenerDeps {
  payments: PaymentClient;
  notifier: NotificationSender;
}

export function registerOrderListeners(bus: EventBus, deps: OrderListenerDeps): void {
  // confirmation e-mail
  bus.subscribe<OrderPlaced>('OrderPlaced', async (e) => {
    await deps.notifier.send(e.customerEmail, 'Your order is confirmed', `Thanks! Order ${e.orderId} is on its way.`);
  });

  // payment capture
  bus.subscribe<OrderPlaced>('OrderPlaced', async (e) => {
    const result = await deps.payments.capture(e.paymentToken, e.amountCents);
    if (!result.ok) {
      throw new Error(`payment declined for order ${e.orderId}`);
    }
  });

  // analytics
  bus.subscribe<OrderPlaced>('OrderPlaced', (e) => {
    console.log(JSON.stringify({ metric: 'order_placed', amountCents: e.amountCents }));
  });
}

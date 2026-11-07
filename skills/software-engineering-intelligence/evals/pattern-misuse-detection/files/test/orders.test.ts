import assert from 'node:assert/strict';
import { test } from 'node:test';
import { EventBus } from '../src/events/EventBus';
import { registerOrderListeners } from '../src/orders/listeners';
import { OrderService } from '../src/orders/OrderService';
import type { PaymentClient } from '../src/payments/PaymentClient';
import { OrderRepository } from '../src/persistence/OrderRepository';
import { PricingService } from '../src/pricing/PricingService';
import { FakeNotificationSender } from './support/fakes';

test('placing an order confirms it and e-mails the customer', async () => {
  const bus = new EventBus();
  const notifier = new FakeNotificationSender();
  const payments = { capture: async () => ({ ok: true, reference: 'cap_1' }) } as unknown as PaymentClient;
  registerOrderListeners(bus, { payments, notifier });
  const service = new OrderService(new OrderRepository(), new PricingService(), bus);

  const order = await service.placeOrder({ lines: [{ sku: 'A', unitPriceCents: 1000, quantity: 2 }] }, 'ann@example.com', 'tok_1');

  assert.equal(order.status, 'CONFIRMED');
  assert.equal(notifier.sent.length, 1);
  assert.equal(notifier.sent[0].to, 'ann@example.com');
});

test('an empty cart is rejected', async () => {
  const service = new OrderService(new OrderRepository(), new PricingService(), new EventBus());
  await assert.rejects(service.placeOrder({ lines: [] }, 'ann@example.com', 'tok_1'));
});

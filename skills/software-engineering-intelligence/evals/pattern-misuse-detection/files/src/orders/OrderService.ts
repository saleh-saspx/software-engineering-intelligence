import { randomUUID } from 'node:crypto';
import type { EventBus } from '../events/EventBus';
import type { OrderRepository } from '../persistence/OrderRepository';
import type { PricingService } from '../pricing/PricingService';
import type { Cart, Order } from './types';

export interface OrderPlaced {
  orderId: string;
  customerEmail: string;
  amountCents: number;
  paymentToken: string;
}

export class OrderService {
  constructor(
    private readonly orders: OrderRepository,
    private readonly pricing: PricingService,
    private readonly bus: EventBus,
  ) {}

  async placeOrder(cart: Cart, customerEmail: string, paymentToken: string): Promise<Order> {
    if (cart.lines.length === 0) {
      throw new Error('cart is empty');
    }
    const order: Order = {
      id: randomUUID(),
      customerEmail,
      amountCents: this.pricing.totalCents(cart),
      status: 'CONFIRMED',
      lines: cart.lines,
    };
    await this.orders.save(order);
    // Payment capture, the confirmation e-mail and analytics run as listeners (see listeners.ts).
    await this.bus.publish<OrderPlaced>('OrderPlaced', {
      orderId: order.id,
      customerEmail,
      amountCents: order.amountCents,
      paymentToken,
    });
    return order;
  }

  findOrder(id: string): Promise<Order | undefined> {
    return this.orders.findById(id);
  }
}

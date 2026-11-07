import type { Order } from '../orders/types';
import { AuditedRepository } from './AuditedRepository';

export class OrderRepository extends AuditedRepository<Order> {
  async findByCustomer(email: string): Promise<Order[]> {
    return [...this.rows.values()].filter((o) => o.customerEmail === email);
  }
}

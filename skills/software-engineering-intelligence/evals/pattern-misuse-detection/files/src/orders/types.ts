export interface CartLine {
  sku: string;
  unitPriceCents: number;
  quantity: number;
}

export interface Cart {
  lines: CartLine[];
}

export type OrderStatus = 'CONFIRMED' | 'CANCELLED';

export interface Order {
  id: string;
  customerEmail: string;
  amountCents: number;
  status: OrderStatus;
  lines: CartLine[];
}

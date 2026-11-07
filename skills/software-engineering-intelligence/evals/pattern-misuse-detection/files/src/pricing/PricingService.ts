import { ConfigManager } from '../config/ConfigManager';
import type { Cart } from '../orders/types';
import { discountFor, type Promotion } from './DiscountStrategy';

export class PricingService {
  constructor(private readonly activePromotion?: Promotion) {}

  totalCents(cart: Cart): number {
    const subtotal = cart.lines.reduce((sum, l) => sum + l.unitPriceCents * l.quantity, 0);
    const promo = this.activePromotion;
    const discount = promo ? discountFor(promo).discountCents(cart, promo) : 0;
    const taxRate = Number(ConfigManager.getInstance().get('taxRate'));
    return Math.round((subtotal - discount) * (1 + taxRate));
  }
}

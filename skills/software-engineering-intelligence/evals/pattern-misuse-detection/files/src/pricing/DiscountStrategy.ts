import type { Cart } from '../orders/types';

export type PromotionType = 'percentage' | 'fixed' | 'buy_x_get_y' | 'tiered';

export interface Promotion {
  type: PromotionType;
  params: Record<string, number>;
}

export interface DiscountStrategy {
  discountCents(cart: Cart, promo: Promotion): number;
}

const subtotal = (cart: Cart): number => cart.lines.reduce((s, l) => s + l.unitPriceCents * l.quantity, 0);

export class PercentageDiscount implements DiscountStrategy {
  discountCents(cart: Cart, promo: Promotion): number {
    return Math.round((subtotal(cart) * promo.params.percent) / 100);
  }
}

export class FixedAmountDiscount implements DiscountStrategy {
  discountCents(cart: Cart, promo: Promotion): number {
    return Math.min(subtotal(cart), promo.params.amountCents);
  }
}

export class BuyXGetYDiscount implements DiscountStrategy {
  // buy `x` units of a line, get `y` of them free (cheapest line first)
  discountCents(cart: Cart, promo: Promotion): number {
    const { x, y } = promo.params;
    return cart.lines
      .map((l) => Math.floor(l.quantity / (x + y)) * y * l.unitPriceCents)
      .reduce((a, b) => a + b, 0);
  }
}

export class TieredDiscount implements DiscountStrategy {
  // params: threshold1Cents, percent1, threshold2Cents, percent2
  discountCents(cart: Cart, promo: Promotion): number {
    const total = subtotal(cart);
    const p = promo.params;
    const percent = total >= p.threshold2Cents ? p.percent2 : total >= p.threshold1Cents ? p.percent1 : 0;
    return Math.round((total * percent) / 100);
  }
}

const STRATEGIES: Record<PromotionType, DiscountStrategy> = {
  percentage: new PercentageDiscount(),
  fixed: new FixedAmountDiscount(),
  buy_x_get_y: new BuyXGetYDiscount(),
  tiered: new TieredDiscount(),
};

export function discountFor(promo: Promotion): DiscountStrategy {
  const strategy = STRATEGIES[promo.type];
  if (!strategy) {
    throw new Error(`unknown promotion type: ${promo.type}`);
  }
  return strategy;
}

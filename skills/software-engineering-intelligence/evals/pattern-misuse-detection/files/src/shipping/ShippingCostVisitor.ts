export interface ShipmentItemVisitor<R> {
  visitParcel(parcel: Parcel): R;
  visitLetter(letter: Letter): R;
}

export interface ShipmentItem {
  accept<R>(visitor: ShipmentItemVisitor<R>): R;
}

export class Parcel implements ShipmentItem {
  constructor(readonly weightGrams: number) {}

  accept<R>(visitor: ShipmentItemVisitor<R>): R {
    return visitor.visitParcel(this);
  }
}

export class Letter implements ShipmentItem {
  constructor(readonly large: boolean) {}

  accept<R>(visitor: ShipmentItemVisitor<R>): R {
    return visitor.visitLetter(this);
  }
}

/** The only visitor: shipping cost in cents. */
export class ShippingCostVisitor implements ShipmentItemVisitor<number> {
  visitParcel(parcel: Parcel): number {
    return 490 + Math.ceil(parcel.weightGrams / 1000) * 150;
  }

  visitLetter(letter: Letter): number {
    return letter.large ? 160 : 85;
  }
}

export function shippingCostCents(items: ShipmentItem[]): number {
  const visitor = new ShippingCostVisitor();
  return items.reduce((sum, item) => sum + item.accept(visitor), 0);
}

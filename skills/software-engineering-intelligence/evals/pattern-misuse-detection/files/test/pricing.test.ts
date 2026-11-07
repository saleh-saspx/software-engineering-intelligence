import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { ConfigManager } from '../src/config/ConfigManager';
import { PricingService } from '../src/pricing/PricingService';

afterEach(() => ConfigManager.reset());

const cart = { lines: [{ sku: 'A', unitPriceCents: 1000, quantity: 3 }] };

test('adds tax from configuration', () => {
  ConfigManager.getInstance().set('taxRate', '0.1');
  assert.equal(new PricingService().totalCents(cart), 3300);
});

test('percentage promotion is applied before tax', () => {
  ConfigManager.getInstance().set('taxRate', '0');
  const pricing = new PricingService({ type: 'percentage', params: { percent: 10 } });
  assert.equal(pricing.totalCents(cart), 2700);
});

test('tiered promotion uses the highest reached tier', () => {
  ConfigManager.getInstance().set('taxRate', '0');
  const pricing = new PricingService({
    type: 'tiered',
    params: { threshold1Cents: 2000, percent1: 5, threshold2Cents: 3000, percent2: 10 },
  });
  assert.equal(pricing.totalCents(cart), 2700);
});

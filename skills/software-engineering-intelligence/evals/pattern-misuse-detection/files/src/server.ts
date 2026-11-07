import { createServer } from 'node:http';
import { ConfigManager } from './config/ConfigManager';
import { EventBus } from './events/EventBus';
import { auth, rateLimit, requestLog } from './http/middleware';
import { compose, type Handler, type Request } from './http/pipeline';
import { NotificationSenderFactory } from './notifications/NotificationSenderFactory';
import { registerOrderListeners } from './orders/listeners';
import { OrderService } from './orders/OrderService';
import type { Cart } from './orders/types';
import { PaymentClient } from './payments/PaymentClient';
import { OrderRepository } from './persistence/OrderRepository';
import { PricingService } from './pricing/PricingService';
import { Letter, Parcel, shippingCostCents } from './shipping/ShippingCostVisitor';

const config = ConfigManager.getInstance();
const bus = new EventBus();
const orders = new OrderRepository();
const notifier = new NotificationSenderFactory().create();
const payments = new PaymentClient(process.env.PAYMENT_API_KEY ?? '');
registerOrderListeners(bus, { payments, notifier });
const orderService = new OrderService(orders, new PricingService(), bus);

const routes: Record<string, Handler> = {
  'POST /orders': async (req) => {
    const { cart, email, paymentToken } = req.body as { cart: Cart; email: string; paymentToken: string };
    const order = await orderService.placeOrder(cart, email, paymentToken);
    return { status: 201, body: order };
  },
  'POST /shipping/estimate': async (req) => {
    const { parcels, letters } = req.body as { parcels: number[]; letters: boolean[] };
    const items = [...parcels.map((g) => new Parcel(g)), ...letters.map((large) => new Letter(large))];
    return { status: 200, body: { cents: shippingCostCents(items) } };
  },
  'POST /admin/config': async (req) => {
    const { key, value } = req.body as { key: string; value: string };
    config.set(key, value);
    return { status: 204 };
  },
};

const app = compose(
  [requestLog, auth(process.env.API_TOKEN ?? ''), rateLimit(Number(config.get('maxRequestsPerMinute')))],
  async (req) => (routes[`${req.method} ${req.path}`] ?? (async () => ({ status: 404 })))(req),
);

createServer((req, res) => {
  let raw = '';
  req.on('data', (chunk) => (raw += chunk));
  req.on('end', async () => {
    const request: Request = {
      method: req.method ?? 'GET',
      path: (req.url ?? '/').split('?')[0],
      headers: req.headers as Record<string, string | undefined>,
      body: raw ? JSON.parse(raw) : undefined,
      ip: req.socket.remoteAddress ?? '',
    };
    try {
      const response = await app(request);
      res.writeHead(response.status, { 'Content-Type': 'application/json' });
      res.end(response.body === undefined ? '' : JSON.stringify(response.body));
    } catch (err) {
      console.error(err);
      res.writeHead(500).end();
    }
  });
}).listen(Number(process.env.PORT ?? 3000));

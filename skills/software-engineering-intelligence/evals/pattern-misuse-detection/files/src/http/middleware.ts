import type { Middleware } from './pipeline';

export const requestLog: Middleware = async (req, next) => {
  const started = Date.now();
  const res = await next(req);
  console.log(`${req.method} ${req.path} ${res.status} ${Date.now() - started}ms`);
  return res;
};

export function auth(apiToken: string): Middleware {
  return async (req, next) => {
    if (req.headers.authorization !== `Bearer ${apiToken}`) {
      return { status: 401, body: { error: 'unauthorized' } };
    }
    return next(req);
  };
}

export function rateLimit(maxPerMinute: number): Middleware {
  const hits = new Map<string, { windowStart: number; count: number }>();
  return async (req, next) => {
    const now = Date.now();
    const entry = hits.get(req.ip);
    if (!entry || now - entry.windowStart > 60_000) {
      hits.set(req.ip, { windowStart: now, count: 1 });
    } else if (++entry.count > maxPerMinute) {
      return { status: 429, body: { error: 'too many requests' } };
    }
    return next(req);
  };
}

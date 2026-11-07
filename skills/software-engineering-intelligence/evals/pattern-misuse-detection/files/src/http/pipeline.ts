export interface Request {
  method: string;
  path: string;
  headers: Record<string, string | undefined>;
  body?: unknown;
  ip: string;
}

export interface Response {
  status: number;
  body?: unknown;
}

export type Handler = (req: Request) => Promise<Response>;
export type Middleware = (req: Request, next: Handler) => Promise<Response>;

/** compose([a, b, c], h) runs a → b → c → h; each middleware may short-circuit. */
export function compose(middlewares: Middleware[], handler: Handler): Handler {
  return middlewares.reduceRight<Handler>((next, mw) => (req) => mw(req, next), handler);
}

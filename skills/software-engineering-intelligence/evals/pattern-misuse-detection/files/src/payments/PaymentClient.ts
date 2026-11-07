export interface CaptureResult {
  ok: boolean;
  reference?: string;
}

/** Thin client for the payment provider's capture API. */
export class PaymentClient {
  constructor(
    private readonly apiKey: string,
    private readonly baseUrl = 'https://api.payments.example.com',
  ) {}

  async capture(token: string, amountCents: number): Promise<CaptureResult> {
    const res = await fetch(`${this.baseUrl}/v1/captures`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, amount: amountCents }),
    });
    if (!res.ok) {
      return { ok: false };
    }
    const body = (await res.json()) as { id: string };
    return { ok: true, reference: body.id };
  }
}

"""Card payments through the provider's REST API."""
from dataclasses import dataclass
from decimal import Decimal


class PaymentError(Exception):
    pass


class ProviderTimeout(Exception):
    """Raised by the transport when the provider does not answer in time."""


@dataclass
class ProviderResponse:
    status_code: int
    body: dict


class PaymentClient:
    def __init__(self, transport, base_url: str, api_key: str, timeout: float = 5.0, attempts: int = 3):
        self.transport = transport
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.attempts = attempts

    def charge(self, order_ref: str, amount: Decimal, currency: str, card_token: str) -> str:
        payload = {"reference": order_ref, "amount": str(amount), "currency": currency, "source": card_token}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        for _ in range(self.attempts):
            try:
                response = self.transport.post(
                    f"{self.base_url}/v1/charges", json=payload, headers=headers, timeout=self.timeout
                )
            except ProviderTimeout:
                continue  # the provider is slow sometimes; try again
            if response.status_code == 201:
                return response.body["id"]
            raise PaymentError(f"charge declined: {response.body.get('error', 'unknown')}")
        raise PaymentError("payment provider unavailable")

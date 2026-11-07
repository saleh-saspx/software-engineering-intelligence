"""requests-based transport for PaymentClient."""
import os

import requests

from .payment import PaymentClient, ProviderResponse, ProviderTimeout


class RequestsTransport:
    def __init__(self):
        self.session = requests.Session()

    def post(self, url, json, headers, timeout):
        try:
            response = self.session.post(url, json=json, headers=headers, timeout=timeout)
        except requests.Timeout as exc:
            raise ProviderTimeout(str(exc)) from exc
        return ProviderResponse(response.status_code, response.json())


def default_client() -> PaymentClient:
    return PaymentClient(RequestsTransport(), os.environ["PAYMENT_API_URL"], os.environ["PAYMENT_API_KEY"])

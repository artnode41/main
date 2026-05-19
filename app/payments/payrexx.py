"""
Payrexx Payment Provider
API docs: https://developers.payrexx.com/reference
"""
import hashlib
import hmac
import base64
import urllib.parse
from decimal import Decimal
from typing import Optional

import requests

from .base import PaymentProvider, PaymentLink


class PayrexxProvider(PaymentProvider):
    BASE_URL = "https://api.payrexx.com/v1.0"

    def __init__(self, instance: str, api_secret: str):
        self.instance = instance
        self.api_secret = api_secret

    def _sign(self, params: dict) -> str:
        """Generate HMAC-SHA256 signature. Preserves insertion order."""
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        raw = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return base64.b64encode(raw).decode("utf-8")

    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        reference: str,
        description: str,
        buyer_email: Optional[str] = None,
        buyer_name: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> PaymentLink:
        amount_minor = int(amount * 100)

        params = {
            "amount": amount_minor,
            "currency": currency,
            "referenceId": reference,
            "title": description[:50],
            "description": description[:200],
            "purpose": description[:50],
        }

        if buyer_email:
            params["fields[email][value]"] = buyer_email
        if buyer_name:
            parts = buyer_name.split(" ", 1)
            params["fields[forename][value]"] = parts[0]
            if len(parts) > 1:
                params["fields[surname][value]"] = parts[1]
        if return_url:
            params["successRedirectUrl"] = return_url
            params["cancelRedirectUrl"] = return_url

        url = f"{self.BASE_URL}/Invoice/?instance={self.instance}"
        response = requests.post(url, data=params,
                                 headers={"X-API-KEY": self.api_secret},
                                 timeout=15)
        response.raise_for_status()

        data = response.json()
        if data.get("status") != "success":
            raise ValueError(f"Payrexx error: {data.get('message', 'Unknown error')}")

        invoice = data["data"][0]
        return PaymentLink(
            provider="payrexx",
            payment_url=invoice["link"],
            payment_id=str(invoice["id"]),
            amount=amount,
            currency=currency,
            reference=reference,
        )

    def delete_payment_link(self, payment_id: str) -> bool:
        """Deactivate/delete a Payrexx invoice."""
        params = {}
        params["ApiSignature"] = self._sign(params)
        url = f"{self.BASE_URL}/Invoice/{payment_id}/?instance={self.instance}"
        response = requests.delete(url, params=params, timeout=15)
        return response.status_code == 200

    def get_payment_status(self, payment_id: str) -> str:
        url = f"{self.BASE_URL}/Invoice/{payment_id}/?instance={self.instance}"
        params = {}
        params["ApiSignature"] = self._sign(params)
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        if data.get("status") != "success":
            return "unknown"

        invoice = data["data"][0]
        status_map = {
            "waiting": "pending",
            "confirmed": "paid",
            "authorized": "paid",
            "declined": "failed",
            "refunded": "failed",
            "cancelled": "cancelled",
            "partially-refunded": "paid",
        }
        return status_map.get(invoice.get("status", ""), "pending")


def get_payment_provider(app):
    instance = app.config.get("PAYREXX_INSTANCE")
    secret = app.config.get("PAYREXX_API_SECRET")
    if not instance or not secret:
        return None
    return PayrexxProvider(instance=instance, api_secret=secret)

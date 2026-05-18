"""
ArtNode Payment Abstraction Layer
Base class for payment providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PaymentLink:
    """Result of a payment link creation request."""
    provider: str
    payment_url: str
    payment_id: str
    amount: Decimal
    currency: str
    reference: str
    expires_at: Optional[str] = None


class PaymentProvider(ABC):
    """Abstract base for all payment providers."""

    @abstractmethod
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
        """Create a payment link and return the URL."""
        ...

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """Return payment status: pending | paid | failed | cancelled."""
        ...

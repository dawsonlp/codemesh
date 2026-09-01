"""Implementations of third-party gateways and external services."""

from __future__ import annotations
from decimal import Decimal
import logging
from sample_project.interfaces import DiscountStrategy, NotificationService, PaymentGateway
from sample_project.models import Money
from sample_project.utils import log_execution

logger = logging.getLogger(__name__)


class StripePaymentGateway:
    """Mock payment gateway implementing PaymentGateway protocol."""

    def __init__(self, api_key: str = "test_key") -> None:
        self.api_key = api_key

    @log_execution
    def charge(self, user_id: str, amount: Money) -> bool:
        """Simulate charging a customer card."""
        logger.info(f"Charging {amount.amount} {amount.currency} to user {user_id}")
        return True

    @log_execution
    def refund(self, transaction_id: str, amount: Money) -> bool:
        """Simulate refunding a transaction."""
        logger.info(f"Refunding {amount.amount} {amount.currency} for txn {transaction_id}")
        return True


class EmailNotificationService:
    """Mock email dispatcher implementing NotificationService protocol."""

    def __init__(self, sender_email: str = "noreply@store.com") -> None:
        self.sender_email = sender_email

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        """Simulate sending an email notification."""
        logger.info(f"Sending email to {recipient}: [{subject}] {message}")
        return True


class PercentageDiscountStrategy:
    """Applies a fractional percentage discount to a price."""

    def __init__(self, discount_fraction: Decimal) -> None:
        if not (Decimal("0") <= discount_fraction <= Decimal("1")):
            raise ValueError("Discount fraction must be between 0 and 1")
        self.discount_fraction = discount_fraction

    def apply_discount(self, original_price: Money) -> Money:
        """Calculate the reduced price."""
        multiplier = Decimal("1.0") - self.discount_fraction
        return original_price.multiply(multiplier)


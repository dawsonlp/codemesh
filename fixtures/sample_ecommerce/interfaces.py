"""Interfaces and abstract protocols defining service boundaries."""

from typing import Protocol, TypeVar, Optional, List
from .models import Money

T = TypeVar("T")


class Repository(Protocol[T]):
    """Generic repository protocol for persisting entities."""

    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by its unique identifier."""
        ...

    def save(self, entity: T) -> None:
        """Persist or update an entity."""
        ...

    def list_all(self) -> List[T]:
        """List all entities currently managed."""
        ...

    def delete(self, entity_id: str) -> bool:
        """Delete an entity by id."""
        ...


class PaymentGateway(Protocol):
    """External payment processor interface."""

    def charge(self, user_id: str, amount: Money) -> bool:
        """Charge a specified monetary amount to a user's payment method."""
        ...

    def refund(self, transaction_id: str, amount: Money) -> bool:
        """Issue a refund for a previously captured transaction."""
        ...


class NotificationService(Protocol):
    """Notification dispatcher protocol."""

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        """Send an alert or confirmation notification to a recipient."""
        ...


class DiscountStrategy(Protocol):
    """Strategy interface for computing order discounts."""

    def apply_discount(self, original_price: Money) -> Money:
        """Compute the discounted price based on specific rules."""
        ...


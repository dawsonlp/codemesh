"""Data models representing entities and value objects in the e-commerce domain."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class OrderStatus(str, Enum):
    """Lifecycle status of a customer order."""
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment transaction states."""
    UNPAID = "unpaid"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


@dataclass(frozen=True)
class Money:
    """Immutable monetary amount with currency code."""
    amount: Decimal
    currency: str = "USD"

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def multiply(self, factor: Decimal) -> Money:
        """Multiply monetary value by a factor."""
        return Money(amount=self.amount * factor, currency=self.currency)


@dataclass
class Address:
    """Physical address representation."""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "USA"


@dataclass
class User:
    """User account entity in the system."""
    user_id: str
    name: str
    email: str
    address: Optional[Address] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def update_email(self, new_email: str) -> None:
        """Update the user's email address."""
        self.email = new_email


@dataclass
class OrderItem:
    """Single item within an order line."""
    item_id: str
    name: str
    unit_price: Money
    quantity: int

    @property
    def total_price(self) -> Money:
        """Compute the total price for this order item line."""
        return self.unit_price.multiply(Decimal(self.quantity))


@dataclass
class Order:
    """Aggregated customer order entity."""
    order_id: str
    user_id: str
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_item(self, item: OrderItem) -> None:
        """Add a line item to the order."""
        self.items.append(item)

    def calculate_subtotal(self) -> Money:
        """Compute the grand total for all items in the order."""
        if not self.items:
            return Money(amount=Decimal("0.00"))
        total = self.items[0].total_price
        for item in self.items[1:]:
            total = total + item.total_price
        return total


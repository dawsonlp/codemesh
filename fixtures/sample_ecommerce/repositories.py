"""Concrete repository implementations using in-memory structures."""

from __future__ import annotations
from typing import Dict, Generic, List, Optional, TypeVar
from .interfaces import Repository
from .models import Order, OrderStatus, User

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    """Generic in-memory storage backing the Repository protocol."""

    def __init__(self) -> None:
        self._storage: Dict[str, T] = {}

    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Fetch item by key from local storage."""
        return self._storage.get(entity_id)

    def save(self, entity_id: str, entity: T) -> None:
        """Store an entity under key."""
        self._storage[entity_id] = entity

    def list_all(self) -> List[T]:
        """Retrieve all active entities."""
        return list(self._storage.values())

    def delete(self, entity_id: str) -> bool:
        """Remove entity if present."""
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False


class OrderRepository(InMemoryRepository[Order]):
    """Repository specialized for Order entities with query extensions."""

    def save_order(self, order: Order) -> None:
        """Save order entity using its order_id attribute."""
        self.save(order.order_id, order)

    def find_by_user_id(self, user_id: str) -> List[Order]:
        """Find all orders belonging to a given user."""
        return [order for order in self.list_all() if order.user_id == user_id]

    def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find orders matching a specific status."""
        return [order for order in self.list_all() if order.status == status]


class UserRepository(InMemoryRepository[User]):
    """Repository specialized for User accounts."""

    def save_user(self, user: User) -> None:
        """Persist a user entity."""
        self.save(user.user_id, user)

    def find_by_email(self, email: str) -> Optional[User]:
        """Look up a user by email address."""
        for user in self.list_all():
            if user.email.lower() == email.lower():
                return user
        return None


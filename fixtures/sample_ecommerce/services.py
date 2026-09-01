"""Core business service orchestrating order lifecycle and payment handling."""

from __future__ import annotations
from typing import List, Optional
from .gateways import EmailNotificationService, StripePaymentGateway
from .interfaces import DiscountStrategy, NotificationService, PaymentGateway
from .models import Money, Order, OrderItem, OrderStatus, PaymentStatus, User
from .repositories import OrderRepository, UserRepository
from .utils import generate_unique_id, log_execution


class OrderProcessingError(Exception):
    """Raised when an order workflow fails validation or payment."""
    pass


class OrderService:
    """Service coordinating order creation, payment settlement, and fulfillment."""

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        payment_gateway: Optional[PaymentGateway] = None,
        notification_service: Optional[NotificationService] = None,
        discount_strategy: Optional[DiscountStrategy] = None,
    ) -> None:
        self.order_repo = order_repo
        self.user_repo = user_repo
        self.payment_gateway = payment_gateway or StripePaymentGateway()
        self.notification_service = notification_service or EmailNotificationService()
        self.discount_strategy = discount_strategy

    @log_execution
    def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        """Create and persist a new customer order.

        Args:
            user_id: The ID of the customer placing the order.
            items: Non-empty list of items to purchase.

        Returns:
            The newly created Order object in PENDING state.

        Raises:
            OrderProcessingError: If the user does not exist or item list is empty.
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise OrderProcessingError(f"User not found: {user_id}")
        if not items:
            raise OrderProcessingError("Cannot create an order with zero items")

        order_id = generate_unique_id("ord")
        order = Order(
            order_id=order_id,
            user_id=user_id,
            items=items,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.UNPAID,
        )
        self.order_repo.save_order(order)
        return order

    @log_execution
    def calculate_order_total(self, order_id: str) -> Money:
        """Calculate the final total for an order applying discount strategies if configured."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderProcessingError(f"Order not found: {order_id}")

        subtotal = order.calculate_subtotal()
        if self.discount_strategy:
            return self.discount_strategy.apply_discount(subtotal)
        return subtotal

    @log_execution
    def checkout_order(self, order_id: str) -> bool:
        """Process payment and update order status for checkout."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderProcessingError(f"Order not found: {order_id}")

        user = self.user_repo.get_by_id(order.user_id)
        if not user:
            raise OrderProcessingError(f"User not found: {order.user_id}")

        amount = self.calculate_order_total(order_id)
        charged = self.payment_gateway.charge(user.user_id, amount)
        if not charged:
            order.payment_status = PaymentStatus.FAILED
            self.order_repo.save_order(order)
            return False

        order.payment_status = PaymentStatus.CAPTURED
        order.status = OrderStatus.PAID
        self.order_repo.save_order(order)

        self.notification_service.send_notification(
            recipient=user.email,
            subject=f"Order Confirmed: {order.order_id}",
            message=f"Thank you for your order! Total charged: {amount.amount} {amount.currency}",
        )
        return True


"""Evaluation test suite verifying Coupon & Loyalty Discount System compliance."""

from decimal import Decimal
import importlib
import sys
import pytest


def run_eval_tests(package_root_path: str):
    """Run all functional compliance tests against an imported package directory."""
    if package_root_path not in sys.path:
        sys.path.insert(0, package_root_path)

    # Dynamic imports
    models = importlib.import_module("sample_ecommerce.models")
    interfaces = importlib.import_module("sample_ecommerce.interfaces")
    services = importlib.import_module("sample_ecommerce.services")
    repositories = importlib.import_module("sample_ecommerce.repositories")
    utils = importlib.import_module("sample_ecommerce.utils")

    # 1. Test Coupon Entity
    assert hasattr(models, "Coupon"), "models.Coupon entity missing"
    min_spend = models.Money(Decimal("50.00"), "USD")
    coupon = models.Coupon(code="SAVE20", discount_percent=0.20, min_order_amount=min_spend, is_active=True)

    assert coupon.is_applicable(models.Money(Decimal("60.00"), "USD")) is True
    assert coupon.is_applicable(models.Money(Decimal("40.00"), "USD")) is False

    # 2. Test CouponDiscountStrategy
    strategy_cls = getattr(interfaces, "CouponDiscountStrategy", None)
    assert strategy_cls is not None, "CouponDiscountStrategy missing in interfaces"

    strategy = strategy_cls(coupon)
    subtotal = models.Money(Decimal("100.00"), "USD")
    discounted = strategy.apply_discount(subtotal)
    assert discounted.amount == Decimal("80.00")
    assert discounted.currency == "USD"

    # Inapplicable discount test
    low_subtotal = models.Money(Decimal("30.00"), "USD")
    assert strategy.apply_discount(low_subtotal).amount == Decimal("30.00")

    # 3. Test OrderService.apply_coupon
    order_repo = repositories.OrderRepository()
    user_repo = repositories.UserRepository()
    user = models.User(user_id="u1", email="test@example.com", name="Alice")
    user_repo.save_user(user)

    item = models.OrderItem(item_id="i1", name="Product", unit_price=models.Money(Decimal("100.00"), "USD"), quantity=1)
    service = services.OrderService(order_repo=order_repo, user_repo=user_repo)
    order = service.create_order(user_id="u1", items=[item])

    assert hasattr(service, "apply_coupon"), "OrderService.apply_coupon method missing"
    final_total = service.apply_coupon(order.order_id, coupon)
    assert final_total.amount == Decimal("80.00")

    # 4. Test format_discount_summary
    assert hasattr(utils, "format_discount_summary"), "utils.format_discount_summary missing"
    summary_text = utils.format_discount_summary("SAVE20", models.Money(Decimal("20.00"), "USD"))
    assert "SAVE20" in summary_text
    assert "20.00" in summary_text

    return True

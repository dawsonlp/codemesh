# Benchmark Task Specification: Coupon & Loyalty Discount System

Extend the core e-commerce package with a structured **Coupon & Loyalty Discount System**.

---

## 1. Requirements

### A. Model Entity (`models.py`)
Add the `Coupon` class:
* Attributes:
  * `code: str`: Unique coupon identifier code (e.g. `"SUMMER20"`).
  * `discount_percent: float`: Discount percentage (e.g. `0.20` for 20% off).
  * `min_order_amount: Money`: Minimum subtotal required to apply the coupon.
  * `is_active: bool = True`: Whether the coupon is currently valid.
* Method:
  * `is_applicable(order_subtotal: Money) -> bool`: Returns `True` if `is_active` is `True` and `order_subtotal.amount >= min_order_amount.amount` (and currencies match).

---

### B. Interface Strategy Implementation (`interfaces.py` or `gateways.py`)
Implement the `CouponDiscountStrategy` class adhering to the `DiscountStrategy` protocol:
* `__init__(coupon: Coupon)`
* `apply_discount(subtotal: Money) -> Money`:
  * If `coupon.is_applicable(subtotal)` is `False`, returns the original `subtotal`.
  * Otherwise, computes `discount = subtotal.amount * Decimal(str(coupon.discount_percent))` and returns `Money(amount=subtotal.amount - discount, currency=subtotal.currency)`.

---

### C. Service Layer Integration (`services.py`)
Update `OrderService`:
* Add method `apply_coupon(order_id: str, coupon: Coupon) -> Money`:
  * Retrieves order from `order_repo`. If not found, raises `OrderProcessingError`.
  * Configures `self.discount_strategy = CouponDiscountStrategy(coupon)`.
  * Returns the discounted order total via `self.calculate_order_total(order_id)`.

---

### D. Utility Helper (`utils.py`)
Add helper function:
* `format_discount_summary(coupon_code: str, discount_amount: Money) -> str`:
  * Returns formatted string: `f"Coupon {coupon_code} applied: -{discount_amount.amount} {discount_amount.currency}"`.


logger = logging.getLogger("sample_project")


F = TypeVar("F", bound=Callable[..., Any])


def generate_unique_id(prefix: str = "id") -> str:
    """Generate a random unique identifier with a given prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def log_execution(func: F) -> F:
    """Decorator to log function entry, exit, and execution time."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__qualname__
        logger.debug(f"Entering {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exited {func_name} successfully")
            return result
        except Exception as exc:
            logger.error(f"Error in {func_name}: {exc}")
            raise
    return wrapper  # type: ignore[return-value]


def format_discount_summary(coupon_code: str, discount_amount: Money) -> str:
    """Format discount applied for telemetry summary."""
    return f"Coupon {coupon_code} applied: -{discount_amount.amount} {discount_amount.currency}"

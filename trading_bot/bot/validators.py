"""
this is the input validation logic,
Validates all order inputs locally before making network calls to catch bad inputs early.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}


def validate_order_input(
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
) -> tuple[str, str, str, float, float | None, float | None]:
    """Validates and standardizes the parameters for an order request"""


    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("'symbol' must be a non-empty string (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()


    if not side or not isinstance(side, str):
        raise ValueError("'side' must be BUY or SELL.")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"'side' must be one of {sorted(VALID_SIDES)}, got '{side}'."
        )


    if not order_type or not isinstance(order_type, str):
        raise ValueError(
            f"'order_type' must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"'order_type' must be one of {sorted(VALID_ORDER_TYPES)}, "
            f"got '{order_type}'."
        )


    if quantity is None:
        raise ValueError("'quantity' is required.")
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"'quantity' must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValueError(
            f"'quantity' must be greater than 0, got {quantity}."
        )

    # price is required for LIMIT and STOP_LIMIT
    if order_type in {"LIMIT", "STOP_LIMIT"}:
        if price is None:
            raise ValueError(
                f"'price' is required for {order_type} orders."
            )
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"'price' must be a number, got '{price}'.")
        if price <= 0:
            raise ValueError(
                f"'price' must be greater than 0, got {price}."
            )
    else:
        # ignore price for MARKET orders so Binance doesn't reject the request
        price = None

    # stop_price is only needed for STOP_LIMIT
    if order_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValueError(
                "'stop_price' is required for STOP_LIMIT orders."
            )
        try:
            stop_price = float(stop_price)
        except (TypeError, ValueError):
            raise ValueError(
                f"'stop_price' must be a number, got '{stop_price}'."
            )
        if stop_price <= 0:
            raise ValueError(
                f"'stop_price' must be greater than 0, got {stop_price}."
            )
    else:
        stop_price = None

    return symbol, side, order_type, quantity, price, stop_price
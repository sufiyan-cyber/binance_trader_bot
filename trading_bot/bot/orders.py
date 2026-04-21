"""
order placement logic for the Binance Futures Testnet.
Provides a clean interface for market, Limit, and Stop-Limit orders,
and normalizes the raw API responses.
"""

from __future__ import annotations

import logging
from typing import Any

from bot.client import BinanceAPIError, BinanceClient

logger = logging.getLogger("trading_bot.orders")

_ORDER_ENDPOINT = "/fapi/v1/order"

# Fields we actually care about returning to the user/CLI
_NORMALISED_KEYS = (
    "orderId",
    "symbol",
    "side",
    "type",
    "status",
    "origQty",
    "executedQty",
    "avgPrice",
)


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """filters the raw API response to return only the essential fields that we need"""
    return {key: raw.get(key, "N/A") for key in _NORMALISED_KEYS}


class OrderManager:
    """Manages order creation using the provided BinanceClient """

    def __init__(self, client: BinanceClient) -> None:
        self._client = client



    def place_market_order(
            self,
            symbol: str,
            side: str,
            quantity: float,
    ) -> dict[str, Any]:
        """
        Places a MARKET order.
        Note: Binance rejects market orders if you send a price parameter.
        """
        logger.info(
            "Placing MARKET order — symbol=%s  side=%s  quantity=%s",
            symbol, side, quantity,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }

        try:
            raw = self._client.signed_request("POST", _ORDER_ENDPOINT, params)
        except BinanceAPIError as exc:
            logger.error(
                "MARKET order failed — symbol=%s  side=%s  error=%s",
                symbol, side, exc,
                exc_info=True,
            )
            raise

        logger.debug("MARKET raw response: %s", raw)
        result = _normalise(raw)
        logger.info(
            "MARKET order confirmed — orderId=%s  status=%s  executedQty=%s  avgPrice=%s",
            result["orderId"], result["status"],
            result["executedQty"], result["avgPrice"],
        )
        return result



    def place_limit_order(
            self,
            symbol: str,
            side: str,
            quantity: float,
            price: float,
    ) -> dict[str, Any]:
        """Places a standard LIMIT order (Good Till Cancelled)"""
        logger.info(
            "Placing LIMIT order — symbol=%s  side=%s  quantity=%s  price=%s",
            symbol, side, quantity, price,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC",
        }

        try:
            raw = self._client.signed_request("POST", _ORDER_ENDPOINT, params)
        except BinanceAPIError as exc:
            logger.error(
                "LIMIT order failed — symbol=%s  side=%s  price=%s  error=%s",
                symbol, side, price, exc,
                exc_info=True,
            )
            raise

        logger.debug("LIMIT raw response: %s", raw)
        result = _normalise(raw)

        # handle the display of unfilled limit orders nicely
        avg = result["avgPrice"]
        display_avg = avg if avg != "0" else "0 (not yet filled)"

        logger.info(
            "LIMIT order acknowledged — orderId=%s  status=%s  executedQty=%s  avgPrice=%s",
            result["orderId"], result["status"],
            result["executedQty"], display_avg,
        )
        return result

    # --- Stop-Limit Order (Bonus) ---

    def place_stop_limit_order(
            self,
            symbol: str,
            side: str,
            quantity: float,
            stop_price: float,
            limit_price: float,
    ) -> dict[str, Any]:
        """
        Places a STOP_LIMIT order.
        Binance uses the 'STOP' type for this. When stop_price is hit,
        a limit order is placed at limit_price.
        """
        logger.info(
            "Placing STOP_LIMIT order — symbol=%s  side=%s  quantity=%s  "
            "stop_price=%s  limit_price=%s",
            symbol, side, quantity, stop_price, limit_price,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "STOP",
            "quantity": quantity,
            "price": limit_price,
            "stopPrice": stop_price,
            "timeInForce": "GTC",
        }

        try:
            raw = self._client.signed_request("POST", _ORDER_ENDPOINT, params)
        except BinanceAPIError as exc:
            logger.error(
                "STOP_LIMIT order failed — symbol=%s  side=%s  "
                "stop_price=%s  limit_price=%s  error=%s",
                symbol, side, stop_price, limit_price, exc,
                exc_info=True,
            )
            raise

        logger.debug("STOP_LIMIT raw response: %s", raw)
        result = _normalise(raw)
        logger.info(
            "STOP_LIMIT order acknowledged — orderId=%s  status=%s  "
            "executedQty=%s  avgPrice=%s",
            result["orderId"], result["status"],
            result["executedQty"], result["avgPrice"],
        )
        return result
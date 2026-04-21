"""
cli.py
The below are the commands that we can use to place orders, limit orders etc
these can be run in powershell better to activate venv first then u can run these
Command-line interface for the Binance Futures Testnet trading bot.

Usage examples
──────────────
  # Market order
  python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit order
  python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 65000

  # Stop-Limit order
  python cli.py place-order --symbol BTCUSDT --side BUY --type STOP_LIMIT \
      --quantity 0.001 --price 65000 --stop-price 64500
"""

from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import validate_order_input


BORDER = "═" * 39
DEFAULT_BASE_URL = "https://demo-fapi.binance.com"




def print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
    stop_price: float | None,
) -> None:
    """ to print the pre-submission order summary table """
    print(f"\n{BORDER}")
    print("  ORDER REQUEST")
    print(BORDER)
    print(f"  {'Symbol':<12}: {symbol}")
    print(f"  {'Side':<12}: {side}")
    print(f"  {'Type':<12}: {order_type}")
    print(f"  {'Quantity':<12}: {quantity}")
    if price is not None:
        print(f"  {'Price':<12}: {price:,.2f}")
    if stop_price is not None:
        print(f"  {'Stop Price':<12}: {stop_price:,.2f}")
    print()


def print_order_confirmed(order: dict) -> None:
    """ to print the successful order confirmation """
    avg = order.get("avgPrice", "0")
    # it shows a friendly message when avgprice is zero (limit not yet filled)
    try:
        avg_display = f"{float(avg):,.2f}" if float(avg) > 0 else "0 (not yet filled)"
    except (TypeError, ValueError):
        avg_display = str(avg)

    executed = order.get("executedQty", "N/A")

    print(BORDER)
    print("  ORDER CONFIRMED")
    print(BORDER)
    print(f"  {'Order ID':<12}: {order.get('orderId', 'N/A')}")
    print(f"  {'Status':<12}: {order.get('status', 'N/A')}")
    print(f"  {'Filled Qty':<12}: {executed}")
    print(f"  {'Avg Price':<12}: {avg_display}")
    print(f"{BORDER}\n")


def print_validation_error(message: str) -> None:
    print(f"\n[VALIDATION ERROR] {message}", file=sys.stderr)


def print_api_error(exc: BinanceAPIError) -> None:
    code_part = f" (code: {exc.error_code})" if exc.error_code is not None else ""
    print(f"\n[API ERROR] {exc.message}{code_part}", file=sys.stderr)


def print_network_error() -> None:
    print(
        "\n[NETWORK ERROR] Could not reach Binance Testnet. "
        "Check your internet connection and try again.",
        file=sys.stderr,
    )



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet — CLI Trading Bot",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # its placeorder subcommand
    po = subparsers.add_parser(
        "place-order",
        help="Submit an order to Binance Futures Testnet",
    )

    po.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair (e.g. BTCUSDT)",
    )
    po.add_argument(
        "--side",
        required=True,
        metavar="BUY|SELL",
        help="Order side: BUY or SELL",
    )
    po.add_argument(
        "--type",
        dest="order_type",
        required=True,
        metavar="MARKET|LIMIT|STOP_LIMIT",
        help="Order type",
    )
    po.add_argument(
        "--quantity",
        required=True,
        type=float,
        metavar="QTY",
        help="Quantity to trade (e.g. 0.001)",
    )
    po.add_argument(
        "--price",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price — required for LIMIT and STOP_LIMIT orders",
    )
    po.add_argument(
        "--stop-price",
        type=float,
        default=None,
        metavar="STOP_PRICE",
        dest="stop_price",
        help="Stop trigger price — required for STOP_LIMIT orders",
    )

    return parser




def handle_place_order(args: argparse.Namespace, logger) -> int:
    """this is the execute place order command

    returns like exit code 0 on success, 1 on any error.
    """

    try:
        symbol, side, order_type, quantity, price, stop_price = validate_order_input(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        logger.error("Validation error: %s", exc, exc_info=True)
        print_validation_error(str(exc))
        return 1


    print_request_summary(symbol, side, order_type, quantity, price, stop_price)


    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    base_url = os.environ.get("BINANCE_BASE_URL", DEFAULT_BASE_URL)

    if not api_key or not api_secret:
        msg = (
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set in your .env file. "
            "Copy .env.example → .env and add your testnet credentials."
        )
        logger.error(msg)
        print_validation_error(msg)
        return 1

    client = BinanceClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
    manager = OrderManager(client)

    # it dispaches  to the appropriate order method
    try:
        if order_type == "MARKET":
            order = manager.place_market_order(symbol, side, quantity)
        elif order_type == "LIMIT":
            order = manager.place_limit_order(symbol, side, quantity, price)
        else:
            order = manager.place_stop_limit_order(
                symbol, side, quantity, stop_price, price
            )
    except BinanceAPIError as exc:
        logger.error("API error placing order: %s", exc, exc_info=True)
        print_api_error(exc)
        return 1
    except (requests.ConnectionError, requests.Timeout):
        logger.error(
            "Network error while contacting Binance Testnet", exc_info=True
        )
        print_network_error()
        return 1


    print_order_confirmed(order)
    return 0





def main() -> None:
    # load_dotenv() loads the data from .env file
    load_dotenv()

   # here we are setting up structured logging before anything
    logger = setup_logging()

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "place-order":
        exit_code = handle_place_order(args, logger)
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

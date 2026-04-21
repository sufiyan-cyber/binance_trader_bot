# Binance Futures Demo Trading Bot

A clean, production-quality Python CLI trading bot for **Binance Futures Demo Trading (USDT-M)**. Built with direct REST API calls (no third-party SDK), HMAC-SHA256 request signing, structured logging, and a layered architecture that separates concerns cleanly.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance API wrapper (signing, requests, error handling)
│   ├── orders.py          # Order placement logic (MARKET, LIMIT, STOP_LIMIT)
│   ├── validators.py      # Input validation — runs before any network call
│   └── logging_config.py  # Dual-handler logging (file: DEBUG, console: INFO)
├── cli.py                 # CLI entry point (argparse sub-commands)
├── requirements.txt       # Pinned dependencies
├── .env.example           # Credential template — copy to .env
├── .gitignore
└── logs/
    └── samples/           # Sample log output committed to the repo
        ├── sample_success.log
        └── sample_error.log
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.10+   |
| pip         | 22+     |

---

## Setup

### 1 — Clone the repository

```bash
git clone https://github.com/sufiyan-cyber/binance_trader_bot.git
cd trading_bot
```

### 2 — Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure API credentials

```bash
cp .env.example .env   # or copy .env.example .env on Windows
```

Open `.env` and fill in your **Binance Futures Demo Trading** credentials:

```dotenv
BINANCE_API_KEY=your_demo_api_key_here
BINANCE_API_SECRET=your_demo_api_secret_here
```

> **Where to get demo keys:** Log in at [https://demo.binance.com](https://demo.binance.com), navigate to **Account → API Management**, and create an API key. See the [Futures API Documentation](https://developers.binance.com/docs/derivatives/) for details.

---

## Usage

All commands follow the same pattern:

```
python cli.py place-order [OPTIONS]
```

### Market Order

Buy 0.001 BTC immediately at the market price:

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Limit Order

Sell 0.001 BTC at a specific price of 65 000 USDT:

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 65000
```

### Stop-Limit Order *(Bonus)*

Buy 0.001 BTC when the price touches 64 500 USDT, with a limit leg at 65 000 USDT:

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_LIMIT \
  --quantity 0.001 \
  --stop-price 64500 \
  --price 65000
```

---

## Console Output

### Success

```
═══════════════════════════════════════
  ORDER REQUEST
═══════════════════════════════════════
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.001

═══════════════════════════════════════
  ORDER CONFIRMED
═══════════════════════════════════════
  Order ID    : 3284729
  Status      : FILLED
  Filled Qty  : 0.001
  Avg Price   : 65,234.50
═══════════════════════════════════════
```

### Validation Error

```
[VALIDATION ERROR] 'side' must be one of ['BUY', 'SELL'], got 'LONG'.
```

### API Error

```
[API ERROR] Signature for this request is not valid. (code: -1022)
```

### Network Error

```
[NETWORK ERROR] Could not reach Binance Demo API. Check your internet connection and try again.
```

---

## Argument Reference

| Flag           | Required                          | Type   | Description                          |
|----------------|-----------------------------------|--------|--------------------------------------|
| `--symbol`     | Always                            | string | Trading pair, e.g. `BTCUSDT`         |
| `--side`       | Always                            | string | `BUY` or `SELL`                      |
| `--type`       | Always                            | string | `MARKET`, `LIMIT`, or `STOP_LIMIT`   |
| `--quantity`   | Always                            | float  | Quantity to trade, e.g. `0.001`      |
| `--price`      | LIMIT and STOP_LIMIT orders only  | float  | Limit price                          |
| `--stop-price` | STOP_LIMIT orders only            | float  | Stop trigger price                   |

---

## Logs

| Location                        | Level | Content                                          |
|---------------------------------|-------|--------------------------------------------------|
| `logs/trading_bot.log`          | DEBUG | Every request, response, signature detail        |
| Console (stderr / stdout)       | INFO  | Clean summaries — order placed, errors, status   |
| `logs/samples/sample_success.log` | —   | Example of a successful MARKET order run         |
| `logs/samples/sample_error.log`   | —   | Example of a validation + API error run          |

The `logs/` directory is created automatically at runtime. Only the `logs/samples/` folder is committed to the repository.

---

## Architecture

```
cli.py  ──►  validators.py   (pure, no I/O)
        ──►  client.py       (HTTP + signing)
        ──►  orders.py       (business logic)
        ──►  logging_config  (setup once, used everywhere)
```

Each layer has a single responsibility:

| Module            | Responsibility                                              |
|-------------------|-------------------------------------------------------------|
| `validators.py`   | Validates and normalises user input before any network call |
| `client.py`       | Handles signing, timestamps, HTTP, and raw error mapping    |
| `orders.py`       | Translates validated args into API calls; normalises output |
| `cli.py`          | Parses CLI args, orchestrates layers, formats terminal UX   |
| `logging_config`  | Configures file (DEBUG) + console (INFO) handlers once      |

---

## Error Handling

| Error type              | CLI output prefix    | Exit code |
|-------------------------|----------------------|-----------|
| Bad user input          | `[VALIDATION ERROR]` | `1`       |
| Binance API rejection   | `[API ERROR]`        | `1`       |
| Network / timeout       | `[NETWORK ERROR]`    | `1`       |
| Success                 | *(none)*             | `0`       |

All errors are also written to `logs/trading_bot.log` at `ERROR` level with full stack traces.

---

## Assumptions

- **Demo trading only.** The default base URL is `https://demo-fapi.binance.com`. Override via `BINANCE_BASE_URL` in `.env` if needed.
- **USDT-M Futures.** All orders target the `/fapi/v1/order` endpoint (USDT-margined perpetuals).
- **No position management.** The bot places orders but does not track open positions, PnL, or margin.
- **No order cancellation or status polling.** Each invocation is a single fire-and-forget order submission.
- **Quantities are passed as-is.** The caller is responsible for respecting the symbol's `LOT_SIZE` filter; use `get_exchange_info()` to retrieve precision rules.
- **STOP_LIMIT maps to Binance type `STOP`.** Binance Futures does not have a `STOP_LIMIT` type; the equivalent is `STOP` with both `price` and `stopPrice`.
- **`avgPrice` of `"0"`** is expected for unfilled limit/stop orders and displayed as `0 (not yet filled)`.

---

## Security Notes

- `.env` is listed in `.gitignore` and must **never** be committed.
- API secrets are never logged — the `signed_request` method strips them before writing to the log file.
- The `recvWindow` is set to 5 000 ms to reduce replay-attack exposure.

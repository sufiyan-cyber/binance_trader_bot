
"""
Client wrapper for the Binance Futures REST API.
Handles request signing, timestamps, and error handling.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger("trading_bot.client")

_DEFAULT_TIMEOUT = 10


class BinanceAPIError(Exception):
    """Custom exception for Binance API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.error_code is not None:
            parts.append(f"Binance code {self.error_code}")
        return " | ".join(parts)


class BinanceClient:
    """Handles connection and requests to Binance Futures API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://demo-fapi.binance.com",
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug(
            "BinanceClient initialised — base_url=%s", self.base_url
        )

    def _sign(self, query_string: str) -> str:
        """Generates the required HMAC-SHA256 signature."""
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def signed_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sends a signed HTTP request to the API."""
        params = dict(params or {})

        # binance needs these parameters for signed endpoints
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        # create the query string and sign it
        query_string = urllib.parse.urlencode(params)
        signature = self._sign(query_string)
        query_string = f"{query_string}&signature={signature}"

        url = f"{self.base_url}{endpoint}"

        # avoid logging the signature for security
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug(
            "→ REQUEST  method=%s  url=%s  params=%s",
            method.upper(),
            url,
            safe_params,
        )

        try:
            if method.upper() in {"GET", "DELETE"}:
                response = self._session.request(
                    method,
                    url,
                    params=query_string,
                    timeout=_DEFAULT_TIMEOUT,
                )
            else:
                response = self._session.request(
                    method,
                    url,
                    data=query_string,
                    timeout=_DEFAULT_TIMEOUT,
                )
        except requests.Timeout:
            logger.error("Request timed out — %s %s", method.upper(), url)
            raise
        except requests.ConnectionError:
            logger.error("Connection failed — %s %s", method.upper(), url)
            raise

        logger.debug(
            "← RESPONSE status=%s  body=%s",
            response.status_code,
            response.text[:2000],  # truncate to avoid spamming the logs
        )

        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: requests.Response) -> dict[str, Any]:
        """Parses the JSON response and checks for API errors."""
        try:
            body: dict = response.json()
        except ValueError:
            raise BinanceAPIError(
                f"Non-JSON response from Binance: {response.text[:500]}",
                status_code=response.status_code,
            )

        # api returns a negative code on error
        if not response.ok or (isinstance(body, dict) and "code" in body and body["code"] < 0):
            error_code = body.get("code") if isinstance(body, dict) else None
            message = body.get("msg", response.reason) if isinstance(body, dict) else response.reason
            raise BinanceAPIError(
                message=str(message),
                status_code=response.status_code,
                error_code=error_code,
            )

        return body

    def get_server_time(self) -> int:
        """Gets server time. Good for checking connection."""
        response = self._session.get(
            f"{self.base_url}/fapi/v1/time",
            timeout=_DEFAULT_TIMEOUT,
        )
        logger.debug(
            "← RESPONSE status=%s  body=%s", response.status_code, response.text
        )
        data = self._handle_response(response)
        server_time: int = data["serverTime"]
        logger.debug("Server time: %d ms", server_time)
        return server_time

    def get_exchange_info(self, symbol: str) -> dict[str, Any]:
        """Gets metadata/rules for a specific trading pair."""
        logger.debug("Fetching exchange info for symbol=%s", symbol)
        response = self._session.get(
            f"{self.base_url}/fapi/v1/exchangeInfo",
            timeout=_DEFAULT_TIMEOUT,
        )
        logger.debug(
            "← RESPONSE status=%s  body_length=%d",
            response.status_code,
            len(response.text),
        )
        data = self._handle_response(response)

        for sym_info in data.get("symbols", []):
            if sym_info.get("symbol") == symbol.upper():
                return sym_info

        raise BinanceAPIError(
            f"Symbol '{symbol}' not found on this exchange.",
            status_code=None,
            error_code=None,
        )

"""Client HTTP per Sportmonks Football API v3."""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import certifi

from src.config import Settings
from src.sportmonks.cache import ResponseCache

logger = logging.getLogger(__name__)


class SportmonksError(Exception):
    """Errore generico API Sportmonks."""


class SportmonksRateLimitError(SportmonksError):
    """Rate limit superato (HTTP 429)."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SportmonksClient:
    def __init__(
        self,
        settings: Settings,
        cache: ResponseCache | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.settings = settings
        self.cache = cache
        self.timeout = timeout
        self.max_retries = max_retries
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def _headers(self) -> dict[str, str]:
        if not self.settings.api_token:
            raise SportmonksError(
                "SPORTMONKS_API_TOKEN non configurato. Imposta .env o usa OFFLINE_MODE=true."
            )
        return {
            "Authorization": self.settings.api_token,
            "Accept": "application/json",
            "User-Agent": "ModelloPrevisionaleCalcistico/0.1",
        }

    def _build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        base = self.settings.base_url.rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{base}{path}"
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"
        return url

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        ttl_seconds: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        cache_key = None
        if self.cache and use_cache and ttl_seconds:
            cache_key = ResponseCache.make_key(path, params)
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", path)
                return cached

        url = self._build_url(path, params)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                request = urllib.request.Request(url, headers=self._headers(), method="GET")
                with urllib.request.urlopen(
                    request, timeout=self.timeout, context=self._ssl_context
                ) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw)

                if self.cache and use_cache and ttl_seconds and cache_key:
                    self.cache.set(cache_key, data, ttl_seconds)
                return data

            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429:
                    retry_after = exc.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else 2.0 * attempt
                    logger.warning("Rate limit 429, attendo %.1fs (tentativo %d)", wait, attempt)
                    if attempt < self.max_retries:
                        time.sleep(wait)
                        last_error = SportmonksRateLimitError(
                            f"Rate limit su {path}: {body}", retry_after=wait
                        )
                        continue
                    raise SportmonksRateLimitError(
                        f"Rate limit su {path} dopo {self.max_retries} tentativi", retry_after=wait
                    ) from exc
                raise SportmonksError(f"HTTP {exc.code} su {path}: {body}") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise SportmonksError(f"Richiesta fallita su {path}: {exc}") from exc

        raise SportmonksError(f"Richiesta fallita su {path}: {last_error}")

import io
import json
from unittest.mock import MagicMock, patch

import pytest
import urllib.error

from src.config import load_settings
from src.sportmonks.cache import ResponseCache
from src.sportmonks.client import SportmonksClient, SportmonksError, SportmonksRateLimitError


@pytest.fixture
def api_settings(monkeypatch):
    monkeypatch.setenv("SPORTMONKS_API_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SPORTMONKS_SYNC", "true")
    monkeypatch.setenv("OFFLINE_MODE", "false")
    return load_settings()


def _mock_http_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


def test_client_sends_authorization_header(api_settings):
    client = SportmonksClient(api_settings)
    with patch("urllib.request.urlopen", return_value=_mock_http_response({"data": []})) as mock_urlopen:
        client.get("/fixtures/date/2025-01-01", ttl_seconds=None, use_cache=False)

    request = mock_urlopen.call_args[0][0]
    assert request.get_header("Authorization") == "secret-token"


def test_client_retries_on_429(api_settings):
    client = SportmonksClient(api_settings, max_retries=2)
    success = _mock_http_response({"data": [{"id": 1}]})

    def side_effect(request, timeout=None, context=None):
        if not hasattr(side_effect, "calls"):
            side_effect.calls = 0
        side_effect.calls += 1
        if side_effect.calls == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                hdrs={"Retry-After": "0"},
                fp=io.BytesIO(b""),
            )
        return success

    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            result = client.get("/fixtures/date/2025-01-01", ttl_seconds=None, use_cache=False)

    assert result == {"data": [{"id": 1}]}
    assert side_effect.calls == 2


def test_client_raises_on_http_error(api_settings):
    client = SportmonksClient(api_settings, max_retries=1)

    def side_effect(request, timeout=None, context=None):
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b"server error"),
        )

    with patch("urllib.request.urlopen", side_effect=side_effect):
        with pytest.raises(SportmonksError, match="HTTP 500"):
            client.get("/fixtures/date/2025-01-01", ttl_seconds=None, use_cache=False)


def test_client_raises_after_exhausted_429_retries(api_settings):
    client = SportmonksClient(api_settings, max_retries=2)

    def side_effect(request, timeout=None, context=None):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs={"Retry-After": "0"},
            fp=io.BytesIO(b""),
        )

    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            with pytest.raises(SportmonksRateLimitError):
                client.get("/fixtures/date/2025-01-01", ttl_seconds=None, use_cache=False)


def test_client_cache_hit_skips_http(api_settings):
    cache = ResponseCache(":memory:")
    client = SportmonksClient(api_settings, cache=cache)
    path = "/fixtures/date/2025-01-01"
    params = {"include": "participants"}
    cached_payload = {"data": [{"id": 99, "cached": True}]}
    cache_key = ResponseCache.make_key(path, params)
    cache.set(cache_key, cached_payload, ttl_seconds=3600)

    try:
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = client.get(path, params=params, ttl_seconds=3600)

        mock_urlopen.assert_not_called()
        assert result == cached_payload
    finally:
        cache.close()


def test_client_requires_token():
    settings = load_settings()
    if settings.api_token:
        pytest.skip("Token presente in .env")
    client = SportmonksClient(settings)
    with pytest.raises(SportmonksError):
        client._headers()

import pytest

from src.config import load_settings
from src.sportmonks.client import SportmonksClient, SportmonksError


def test_client_requires_token_when_not_offline():
    settings = load_settings()
    if settings.is_offline:
        pytest.skip("Offline mode attivo")
    client = SportmonksClient(settings)
    with pytest.raises(SportmonksError):
        client._headers()

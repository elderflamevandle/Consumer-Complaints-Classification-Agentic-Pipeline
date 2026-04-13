from __future__ import annotations

import pytest

from src.config import get_settings


def test_mongo_settings_default_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('MONGO_URI', raising=False)
    monkeypatch.setenv('MONGO_DATABASE', 'consumer_complaints_classification')
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.mongo_uri is None
    assert settings.mongo_database == 'consumer_complaints_classification'


def test_get_mongo_client_requires_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.tools.mongo_client import get_mongo_client

    monkeypatch.delenv('MONGO_URI', raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match='MONGO_URI'):
        get_mongo_client()

from src.config import Settings


def test_default_settings():
    s = Settings()
    assert s.embedding_dim == 384
    assert s.api_port == 8000


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("API_PORT", "9001")
    s = Settings()
    assert s.api_port == 9001

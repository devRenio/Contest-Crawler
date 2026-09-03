from collector.config import DEFAULT_DATABASE_URL, Settings


def test_empty_database_url_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    settings = Settings(_env_file=None)
    assert settings.database_url == DEFAULT_DATABASE_URL


def test_whitespace_database_url_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    settings = Settings(_env_file=None)
    assert settings.database_url == DEFAULT_DATABASE_URL

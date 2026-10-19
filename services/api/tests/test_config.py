from app.core.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.app_name == "ai-lms"
    assert settings.app_env == "development"
    assert not settings.is_production
    get_settings.cache_clear()


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/lms")
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.is_production
    assert "lms" in settings.database_url
    get_settings.cache_clear()


def test_reserved_integrations_default_unset():
    settings = Settings(_env_file=None)
    assert settings.redis_url is None
    assert settings.oidc_issuer_url is None

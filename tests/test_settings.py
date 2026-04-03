from config.settings import Settings


def test_sync_database_url_for_sqlite():
    settings = Settings(database_url="sqlite+aiosqlite:///./data/privategpt.db")
    assert settings.sync_database_url == "sqlite:///./data/privategpt.db"


def test_sync_database_url_for_postgres():
    settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost:5432/privategpt")
    assert settings.sync_database_url == "postgresql+psycopg://user:pass@localhost:5432/privategpt"

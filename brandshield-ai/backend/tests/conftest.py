import pytest
from app.config import settings
from app.database import get_database, ping_database


@pytest.fixture(scope="session", autouse=True)
def enforce_test_database_safety():
    """
    CRITICAL SAFETY GUARD:
    Tests must refuse to run if TEST_DATABASE_NAME is missing or equals DATABASE_NAME.
    This guarantees tests can never wipe or mutate application or demo data.
    """
    if not settings.TEST_DATABASE_NAME:
        raise RuntimeError("TEST_DATABASE_NAME is not set. Tests cannot run without an isolated test database.")

    if settings.TEST_DATABASE_NAME.strip().lower() == settings.DATABASE_NAME.strip().lower():
        raise RuntimeError(
            f"REFUSING TO RUN TESTS: TEST_DATABASE_NAME '{settings.TEST_DATABASE_NAME}' "
            f"matches active DATABASE_NAME '{settings.DATABASE_NAME}'. Tests must use an isolated database."
        )


@pytest.fixture(autouse=True)
def point_to_test_database(monkeypatch):
    """
    Ensure all default CRUD operations during tests run exclusively
    against settings.TEST_DATABASE_NAME (brandshield_test).
    """
    monkeypatch.setattr(settings, "DATABASE_NAME", settings.TEST_DATABASE_NAME)
    
    # Check if database is reachable before attempting cleanup
    is_connected, _ = ping_database()
    if is_connected:
        db = get_database(settings.TEST_DATABASE_NAME)
        # Clear collections in test database before each test
        db["brands"].delete_many({})
        db["candidates"].delete_many({})
    yield


@pytest.fixture
def test_db_name():
    """Fixture providing the safe test database name."""
    return settings.TEST_DATABASE_NAME

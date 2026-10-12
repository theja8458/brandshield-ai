import logging
from typing import Optional, Tuple
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger("brandshield.database")

_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    """Retrieve or create the singleton MongoClient."""
    global _client
    if _client is None:
        # Avoid logging the raw URI to protect credentials
        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
            socketTimeoutMS=2500,
        )
    return _client


def get_database(db_name: Optional[str] = None) -> Database:
    """Retrieve the designated MongoDB database."""
    client = get_mongo_client()
    target_name = db_name or settings.DATABASE_NAME
    return client[target_name]


def ping_database() -> Tuple[bool, str]:
    """
    Check if MongoDB Atlas is reachable and responsive.
    Returns (True, "connected") if ping command succeeds,
    or (False, <sanitized_error>) if unreachable.
    Never exposes credentials or full connection strings.
    """
    try:
        client = get_mongo_client()
        # Admin command ping verifies end-to-end server connectivity
        client.admin.command("ping")
        return True, "connected"
    except PyMongoError as err:
        logger.warning("MongoDB ping failed: %s", type(err).__name__)
        return False, f"Database unreachable: {type(err).__name__}"
    except Exception as err:
        logger.warning("Unexpected error during database ping: %s", type(err).__name__)
        return False, "Database connection check failed"


def close_database() -> None:
    """Close the active MongoDB connection pool."""
    global _client
    if _client is not None:
        _client.close()
        _client = None

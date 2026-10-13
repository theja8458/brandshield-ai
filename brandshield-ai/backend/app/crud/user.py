import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo.collection import Collection

from app.database import get_database
from app.schemas.auth import UserCreate, UserResponse, UserRole
from app.services.auth import hash_password

logger = logging.getLogger("brandshield.crud.user")


def get_users_collection() -> Collection:
    """Retrieve the 'users' MongoDB collection."""
    db = get_database()
    col = db["users"]
    # Ensure unique index on email
    try:
        col.create_index("email", unique=True, background=True)
    except Exception as e:
        logger.debug("Index creation check: %s", e)
    return col


def user_doc_to_response(doc: Dict[str, Any]) -> UserResponse:
    """Convert MongoDB user document to public UserResponse (strips password)."""
    return UserResponse(
        user_id=doc["user_id"],
        email=doc["email"],
        role=UserRole(doc.get("role", UserRole.ANALYST.value)),
        is_active=doc.get("is_active", True),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        last_login=doc.get("last_login"),
    )


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve raw user document by normalized email (internal use only)."""
    col = get_users_collection()
    normalized = email.strip().lower()
    return col.find_one({"email": normalized})


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve raw user document by user_id."""
    col = get_users_collection()
    return col.find_one({"user_id": user_id})


def create_user(user_in: UserCreate, is_active: bool = True) -> UserResponse:
    """Create a new user with hashed password."""
    col = get_users_collection()
    normalized_email = user_in.email.strip().lower()
    
    # Check duplicate
    if col.find_one({"email": normalized_email}):
        raise ValueError(f"User with email '{normalized_email}' already exists.")

    user_id = f"usr-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    hashed = hash_password(user_in.password)

    user_doc = {
        "user_id": user_id,
        "email": normalized_email,
        "hashed_password": hashed,
        "role": user_in.role.value,
        "is_active": is_active,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }

    col.insert_one(user_doc)
    logger.info("Created user %s with role %s", user_id, user_in.role.value)
    return user_doc_to_response(user_doc)


def list_users() -> List[UserResponse]:
    """List all registered users without credentials."""
    col = get_users_collection()
    docs = col.find().sort("created_at", -1)
    return [user_doc_to_response(doc) for doc in docs]


def update_last_login(user_id: str) -> None:
    """Record successful login timestamp."""
    col = get_users_collection()
    now = datetime.now(timezone.utc)
    col.update_one({"user_id": user_id}, {"$set": {"last_login": now, "updated_at": now}})


def count_admins() -> int:
    """Count number of active admin users in database."""
    col = get_users_collection()
    return col.count_documents({"role": UserRole.ADMIN.value, "is_active": True})

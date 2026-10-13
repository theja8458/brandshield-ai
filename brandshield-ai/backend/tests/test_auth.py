from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.crud.user import (
    create_user,
    get_user_by_email,
)
from app.schemas.auth import UserCreate, UserRole
from app.services.auth import create_access_token, login_rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


def test_successful_login():
    """Verify that a valid user can authenticate and receive a JWT token."""
    user_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    create_user(user_in)

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@brandshield.ai", "password": "ValidPassword123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "analyst@brandshield.ai"
    assert data["user"]["role"] == "analyst"
    assert data["expires_in"] > 0


def test_incorrect_password():
    """Verify generic 401 error on wrong password."""
    user_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    create_user(user_in)

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@brandshield.ai", "password": "WrongPassword999!"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_unknown_email():
    """Verify generic 401 error on unregistered email."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@brandshield.ai", "password": "AnyPassword123!"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_disabled_account_login():
    """Verify disabled account cannot log in."""
    user_in = UserCreate(
        email="disabled@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    create_user(user_in, is_active=False)

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "disabled@brandshield.ai", "password": "ValidPassword123!"},
    )
    assert res.status_code == 401
    assert "disabled" in res.json()["detail"].lower()


def test_disabled_account_with_valid_token():
    """Verify disabled user is rejected even with a valid signed token."""
    user_in = UserCreate(
        email="suspended@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    user = create_user(user_in, is_active=False)
    token, _ = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role.value})

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "disabled" in res.json()["detail"].lower()


def test_expired_token():
    """Verify expired token returns 401."""
    user_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    user = create_user(user_in)
    # Generate token already expired 5 minutes ago
    token, _ = create_access_token(
        {"sub": user.user_id, "email": user.email, "role": user.role.value},
        expires_delta=timedelta(minutes=-5),
    )

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_invalid_tampered_token():
    """Verify tampered token signature is rejected with 401."""
    user_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    user = create_user(user_in)
    token, _ = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role.value})
    
    # Tamper token signature
    tampered_token = token[:-5] + "XXXXX"

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


def test_missing_authentication_on_protected_endpoints():
    """Verify protected endpoints reject requests with 401 when no token is supplied."""
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/brands"),
        ("GET", "/api/v1/dashboard/metrics"),
        ("GET", "/api/v1/investigations/candidates"),
        ("GET", "/api/v1/campaigns/graph"),
        ("POST", "/api/v1/auth/logout"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path)
        assert res.status_code == 401, f"Expected 401 for {method} {path}, got {res.status_code}"


def test_analyst_permitted_access():
    """Verify analyst can access permitted operational endpoints."""
    user_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    user = create_user(user_in)
    token, _ = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Access /api/v1/auth/me
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "analyst@brandshield.ai"

    # Access /api/v1/brands
    res_brands = client.get("/api/v1/brands", headers=headers)
    assert res_brands.status_code == 200


def test_analyst_denied_on_administrator_endpoints():
    """Verify analyst receives 403 Forbidden when attempting admin operations."""
    analyst_in = UserCreate(
        email="analyst@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    analyst = create_user(analyst_in)
    token, _ = create_access_token({"sub": analyst.user_id, "email": analyst.email, "role": analyst.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to create new user
    res = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={"email": "newuser@brandshield.ai", "password": "Password123!", "role": "analyst"},
    )
    assert res.status_code == 403
    assert "administrator" in res.json()["detail"].lower()

    # Attempt to list users
    res_list = client.get("/api/v1/auth/users", headers=headers)
    assert res_list.status_code == 403


def test_admin_authorization_on_admin_endpoints():
    """Verify admin can create and list users."""
    admin_in = UserCreate(
        email="admin@brandshield.ai",
        password="AdminPassword123!",
        role=UserRole.ADMIN,
    )
    admin = create_user(admin_in)
    token, _ = create_access_token({"sub": admin.user_id, "email": admin.email, "role": admin.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Admin creates new analyst account
    res = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={"email": "subanalyst@brandshield.ai", "password": "Password123!", "role": "analyst"},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["email"] == "subanalyst@brandshield.ai"
    assert created["role"] == "analyst"

    # Admin lists users
    res_list = client.get("/api/v1/auth/users", headers=headers)
    assert res_list.status_code == 200
    users = res_list.json()
    emails = [u["email"] for u in users]
    assert "admin@brandshield.ai" in emails
    assert "subanalyst@brandshield.ai" in emails


def test_duplicate_email_prevention():
    """Verify registering a duplicate email returns 409 Conflict."""
    admin_in = UserCreate(
        email="admin@brandshield.ai",
        password="AdminPassword123!",
        role=UserRole.ADMIN,
    )
    admin = create_user(admin_in)
    token, _ = create_access_token({"sub": admin.user_id, "email": admin.email, "role": admin.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # First creation succeeds
    res1 = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={"email": "duplicate@brandshield.ai", "password": "Password123!", "role": "analyst"},
    )
    assert res1.status_code == 201

    # Second creation with same email fails with 409
    res2 = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={"email": "duplicate@brandshield.ai", "password": "Password123!", "role": "analyst"},
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_password_hashes_stored_never_plaintext():
    """Verify passwords are never stored in plaintext and never leaked in responses."""
    plaintext = "SuperSecretPassword123!"
    user_in = UserCreate(
        email="audit@brandshield.ai",
        password=plaintext,
        role=UserRole.ANALYST,
    )
    user_resp = create_user(user_in)

    # 1. API response schema must not contain password or hash
    assert not hasattr(user_resp, "password")
    assert not hasattr(user_resp, "hashed_password")
    resp_dict = user_resp.model_dump()
    assert "password" not in resp_dict
    assert "hashed_password" not in resp_dict

    # 2. Database document must store Argon2 hash, NEVER plaintext
    doc = get_user_by_email("audit@brandshield.ai")
    assert doc is not None
    assert doc["hashed_password"] != plaintext
    assert doc["hashed_password"].startswith("$argon2")


def test_logout_endpoint():
    """Verify logout endpoint responds cleanly with 200 for authenticated user."""
    user_in = UserCreate(
        email="logoutuser@brandshield.ai",
        password="ValidPassword123!",
        role=UserRole.ANALYST,
    )
    user = create_user(user_in)
    token, _ = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role.value})

    res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

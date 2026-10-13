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


def test_successful_registration():
    """Verify that a new user can register publicly and receive an analyst token."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Analyst",
            "email": "jane.analyst@brandshield.ai",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "jane.analyst@brandshield.ai"
    assert data["user"]["full_name"] == "Jane Analyst"
    assert data["user"]["role"] == "analyst"


def test_registration_duplicate_email():
    """Verify that registering an already existing email returns 409 Conflict."""
    payload = {
        "full_name": "First User",
        "email": "duplicate.reg@brandshield.ai",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_registration_invalid_email_and_weak_password():
    """Verify registration rejects invalid emails and weak passwords."""
    # Invalid email
    res_bad_email = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "not-an-email",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert res_bad_email.status_code == 422

    # Weak password (< 8 chars)
    res_weak_pass = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "valid.user@brandshield.ai",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert res_weak_pass.status_code == 422


def test_registration_password_confirmation_mismatch():
    """Verify registration rejects mismatched password confirmation."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "mismatch@brandshield.ai",
            "password": "SecurePassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    assert res.status_code == 422
    assert "passwords do not match" in res.text.lower()


def test_registration_attempted_admin_role_injection():
    """
    CRITICAL SECURITY TEST:
    Verify that an attacker attempting to pass role='admin' in public registration
    is completely blocked from escalating privilege and is assigned 'analyst' only.
    """
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Sneaky Attacker",
            "email": "attacker@brandshield.ai",
            "password": "MaliciousPassword123!",
            "confirm_password": "MaliciousPassword123!",
            "role": "admin",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["role"] == "analyst"

    # Verify directly in MongoDB Atlas collection
    doc = get_user_by_email("attacker@brandshield.ai")
    assert doc is not None
    assert doc["role"] == "analyst"


def test_successful_login_after_registration():
    """Verify that a registered user can log in via /api/v1/auth/login."""
    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Returning User",
            "email": "returning@brandshield.ai",
            "password": "LoginPassword123!",
            "confirm_password": "LoginPassword123!",
        },
    )
    assert reg_res.status_code == 201

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "returning@brandshield.ai",
            "password": "LoginPassword123!",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "returning@brandshield.ai"
    assert login_data["user"]["role"] == "analyst"


def test_newly_registered_analyst_denied_admin_endpoints():
    """Verify that newly registered users are denied access to admin-only endpoints."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Standard Analyst",
            "email": "standard.analyst@brandshield.ai",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt admin endpoint: GET /api/v1/auth/users
    res_list = client.get("/api/v1/auth/users", headers=headers)
    assert res_list.status_code == 403

    # Attempt admin endpoint: POST /api/v1/auth/users
    res_create = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={"email": "victim@brandshield.ai", "password": "Password123!", "role": "analyst"},
    )
    assert res_create.status_code == 403


def test_existing_admin_login_still_works():
    """Verify that existing administrator accounts can still log in and perform admin actions."""
    admin_in = UserCreate(
        full_name="Master Administrator",
        email="superadmin@brandshield.ai",
        password="SuperAdminPassword123!",
        role=UserRole.ADMIN,
    )
    create_user(admin_in)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "superadmin@brandshield.ai",
            "password": "SuperAdminPassword123!",
        },
    )
    assert res.status_code == 200
    admin_token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Verify admin can access admin users list
    res_users = client.get("/api/v1/auth/users", headers=headers)
    assert res_users.status_code == 200

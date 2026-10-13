from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user, require_admin
from app.crud.user import (
    create_user,
    get_user_by_email,
    list_users,
    update_last_login,
    user_doc_to_response,
)
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    login_rate_limiter,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def api_login(credentials: LoginRequest, request: Request):
    """
    Authenticate user with email and password.
    Returns signed JWT access token and user profile.
    Generic 401 error message protects against account enumeration.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{credentials.email}:{client_ip}"

    if login_rate_limiter.is_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in a few minutes.",
        )

    user_doc = get_user_by_email(credentials.email)
    if not user_doc or not verify_password(credentials.password, user_doc.get("hashed_password", "")):
        login_rate_limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Success: reset limiter and record login
    login_rate_limiter.record_success(rate_key)
    update_last_login(user_doc["user_id"])

    token, expires_in = create_access_token({
        "sub": user_doc["user_id"],
        "email": user_doc["email"],
        "role": user_doc["role"],
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_doc_to_response(user_doc),
    )


@router.get("/me", response_model=UserResponse)
def api_get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user),
):
    """Retrieve details of the currently authenticated user."""
    return current_user


@router.post("/logout", response_model=MessageResponse)
def api_logout(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Log out the current user session.
    Stateless JWT logout invalidates client token on frontend.
    """
    return MessageResponse(
        status="ok",
        message="Session successfully terminated",
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def api_create_user(
    user_in: UserCreate,
    admin_user: UserResponse = Depends(require_admin),
):
    """
    Administrator-only endpoint to create new analyst or administrator accounts.
    Enforces role-based permissions and email uniqueness.
    """
    try:
        created = create_user(user_in)
        return created
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        )


@router.get("/users", response_model=List[UserResponse])
def api_list_users(
    admin_user: UserResponse = Depends(require_admin),
):
    """
    Administrator-only endpoint to view registered accounts.
    Never returns password hashes or credentials.
    """
    return list_users()

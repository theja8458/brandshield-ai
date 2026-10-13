import argparse
import getpass
import os
import sys

from app.crud.user import count_admins, create_user, get_user_by_email
from app.database import ping_database
from app.schemas.auth import UserCreate, UserRole


def main() -> None:
    """
    Safely bootstrap the initial BrandShield AI administrator account.
    Refuses to execute if an administrator already exists or if the email is taken.
    Reads credentials from CLI arguments, environment variables, or interactive prompt.
    """
    parser = argparse.ArgumentParser(
        description="Bootstrap the initial BrandShield AI administrator account."
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Administrator email (or set BOOTSTRAP_ADMIN_EMAIL env var)",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Administrator password (or set BOOTSTRAP_ADMIN_PASSWORD env var)",
    )

    args = parser.parse_args()

    # Step 1: Verify database connection
    is_connected, msg = ping_database()
    if not is_connected:
        print(f"[ERROR] Database connection failed: {msg}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Check if any admin already exists
    existing_admin_count = count_admins()
    if existing_admin_count > 0:
        print(
            f"[NOTICE] Bootstrap refused: {existing_admin_count} administrator account(s) already exist in the database.",
            file=sys.stderr,
        )
        print("To create additional users, log in as an administrator via the UI or API.", file=sys.stderr)
        sys.exit(0)

    # Step 3: Resolve email
    email = (
        args.email
        or os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        or input("Enter initial admin email: ").strip()
    )
    if not email:
        print("[ERROR] Administrator email is required.", file=sys.stderr)
        sys.exit(1)

    # Step 4: Resolve password
    password = (
        args.password
        or os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    )
    if not password:
        password = getpass.getpass("Enter initial admin password (min 8 chars): ").strip()

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    # Step 5: Check if email already registered
    if get_user_by_email(email):
        print(f"[ERROR] An account with email '{email}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Step 6: Create admin account
    try:
        user_in = UserCreate(
            email=email,
            password=password,
            role=UserRole.ADMIN,
        )
        admin = create_user(user_in, is_active=True)
        print("=" * 60)
        print("[SUCCESS] Initial administrator account created successfully!")
        print(f"  User ID : {admin.user_id}")
        print(f"  Email   : {admin.email}")
        print(f"  Role    : {admin.role.value}")
        print("=" * 60)
    except Exception as err:
        print(f"[ERROR] Failed to create administrator: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

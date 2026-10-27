import hashlib
import hmac
import os

from fastapi import HTTPException, Request

# Shared password for the private pages (serials, books). It's a light gate against casual
# visitors, not real security.
PASSWORD = os.environ.get("SERIALS_PASSWORD", "")
COOKIE = "serials_auth"
MAX_AGE = 400 * 24 * 60 * 60  # browsers cap cookie lifetimes at about 400 days
PRIVATE_HEADERS = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}


def token() -> str:
    # Derived from the password, so changing SERIALS_PASSWORD signs out every browser.
    return hmac.new(PASSWORD.encode(), b"serials-auth", hashlib.sha256).hexdigest()


def authorized(request: Request) -> bool:
    return not PASSWORD or hmac.compare_digest(request.cookies.get(COOKIE, ""), token())


def password_ok(password: str) -> bool:
    return bool(PASSWORD) and hmac.compare_digest(password.encode(), PASSWORD.encode())


def require(request: Request) -> None:
    """Dependency for private API routes."""
    if not authorized(request):
        raise HTTPException(401, "Not signed in")

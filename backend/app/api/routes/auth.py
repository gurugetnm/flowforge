"""Registration, sign in and sign out."""

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import create_session_token, hash_password, needs_rehash, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, settings: SettingsDep, user: User) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=create_session_token(str(user.id)),
        max_age=settings.access_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _normalise_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
) -> User:
    """Create an account and start a session for it."""
    email = _normalise_email(payload.email)

    existing = session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        raise ConflictError("An account with that email already exists.")

    user = User(email=email, name=payload.name, password_hash=hash_password(payload.password))
    session.add(user)
    session.flush()

    _set_session_cookie(response, settings, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
) -> User:
    """Exchange credentials for a session cookie."""
    email = _normalise_email(payload.email)
    user = session.scalar(select(User).where(func.lower(User.email) == email))

    # The same message is returned for an unknown email and a wrong password so
    # the endpoint cannot be used to enumerate accounts.
    invalid = AuthenticationError("Email or password is incorrect.")
    if user is None or not user.is_active:
        # Spend comparable time either way to avoid a timing oracle.
        verify_password(payload.password, hash_password("placeholder-comparison"))
        raise invalid
    if not verify_password(payload.password, user.password_hash):
        raise invalid

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    _set_session_cookie(response, settings, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(settings: SettingsDep, response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(key=settings.cookie_name, path="/")


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser) -> User:
    """Return the signed-in account. Used by the client to restore a session."""
    return current_user

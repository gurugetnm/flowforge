"""Shared FastAPI dependencies."""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.core.security import read_session_token
from app.db.session import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    session: SessionDep,
    flowforge_session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Resolve the signed-in user from the session cookie.

    Raises ``AuthenticationError`` for a missing, malformed, expired or
    deactivated session. The message never distinguishes between those cases.
    """
    if not flowforge_session:
        raise AuthenticationError("Sign in to continue.")

    subject = read_session_token(flowforge_session)
    if subject is None:
        raise AuthenticationError("Your session has expired. Sign in again.")

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise AuthenticationError("Your session has expired. Sign in again.") from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Your session has expired. Sign in again.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

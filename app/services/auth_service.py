from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import email_already_registered, invalid_credentials
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.lower()
    return db.scalar(select(User).where(User.email == normalized_email))


def register_user(db: Session, payload: UserRegister) -> TokenResponse:
    if get_user_by_email(db, payload.email) is not None:
        raise email_already_registered()

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


def login_user(db: Session, payload: UserLogin) -> TokenResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials()
    return TokenResponse(access_token=create_access_token(user.id))

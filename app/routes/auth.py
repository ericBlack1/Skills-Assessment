from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import TokenResponse, UserLogin, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register_user(payload: UserRegister, db: DbSession) -> TokenResponse:
    return auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT",
)
def login_user(payload: UserLogin, db: DbSession) -> TokenResponse:
    return auth_service.login_user(db, payload)

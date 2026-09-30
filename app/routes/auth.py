from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import AuthSuccessResponse, UserLogin, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register_user(payload: UserRegister, db: DbSession) -> AuthSuccessResponse:
    token = auth_service.register_user(db, payload)
    return AuthSuccessResponse(
        message="Registration successful",
        data=token,
    )


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    summary="Log in and receive a JWT",
)
def login_user(payload: UserLogin, db: DbSession) -> AuthSuccessResponse:
    token = auth_service.login_user(db, payload)
    return AuthSuccessResponse(
        message="Login successful",
        data=token,
    )

from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.schemas.response import SuccessResponse


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenData(BaseModel):
    """OAuth 2.0 token fields returned inside the success envelope."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")

    @classmethod
    def from_access_token(cls, access_token: str) -> "TokenData":
        return cls(
            access_token=access_token,
            expires_in=settings.jwt_expire_minutes * 60,
        )


class AuthSuccessResponse(SuccessResponse[TokenData]):
    pass

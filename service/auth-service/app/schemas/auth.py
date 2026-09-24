import uuid

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError(
            "Password must be at least 8 characters long"
        )

    if len(password) > 128:
        raise ValueError(
            "Password must not exceed 128 characters"
        )

    if not any(char.isupper() for char in password):
        raise ValueError(
            "Password must contain at least one uppercase letter"
        )

    if not any(char.islower() for char in password):
        raise ValueError(
            "Password must contain at least one lowercase letter"
        )

    if not any(char.isdigit() for char in password):
        raise ValueError(
            "Password must contain at least one number"
        )

    if not any(not char.isalnum() for char in password):
        raise ValueError(
            "Password must contain at least one special character"
        )

    return password


class RegisterRequest(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    workspace_name: str = Field(
        min_length=2,
        max_length=100,
    )

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_strength(password)


class RegisterResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    workspace_id: uuid.UUID

    model_config = {
        "from_attributes": True
    }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_strength(password)


class ResetPasswordResponse(BaseModel):
    message: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str
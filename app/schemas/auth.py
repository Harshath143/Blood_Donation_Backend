from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.security import validate_password_strength

class UserRegister(BaseModel):
    email: EmailStr
    phone: str = Field(..., max_length=20)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., max_length=255)
    role: str = Field("donor", max_length=20)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters, include an uppercase letter, a lowercase letter, a digit, and a special character."
            )
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    full_name: str

class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters, include an uppercase letter, a lowercase letter, a digit, and a special character."
            )
        return v


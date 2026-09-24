from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    workspace_name: str = Field(min_length=2, max_length=100)


class RegisterResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    workspace_id: str
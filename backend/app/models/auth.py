from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+$")


class UserOut(BaseModel):
    user_name: str
    name: str
    title: str
    unit: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut

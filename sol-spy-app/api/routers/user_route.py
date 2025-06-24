from operator import truediv
from sys import prefix

from fastapi import APIRouter, Depends, HTTPException
from poetry.utils.authenticator import Authenticator
from core.models.user import User
from fastapi.security import APIKeyHeader
from api.routers.auth_utils import TokenUtils
from pydantic import BaseModel
from core.db_helper import db_helper

router = APIRouter(prefix="/users", tags=["Users"])


class AuthenticationRequest(BaseModel):
    login: str
    password: str

class AuthenticationResponse(BaseModel):
    id: int | None
    access_token: str
    user_id: int | None

    class Config:
        from_attributes=True

class UserModelResponse(BaseModel):
    id: int | None
    name: str | None
    login: str | None

    class Config:
        from_attributes=True




async def get_token_utils():
    return TokenUtils(db_helper.session_factory)

async def verify_token(
        access_token_code: str = Depends(APIKeyHeader(name="Authorization", auto_error=True)),
        token_utils: TokenUtils = Depends(get_token_utils)
):
    return await token_utils.verify_token(access_token_code)


@router.post("/login",response_model=AuthenticationResponse)
async def login(
        request: AuthenticationRequest,
        token_utils: TokenUtils=Depends(get_token_utils),
):
    try:
        access_token =await token_utils.add_access_token(request.login,request.password)
        return access_token
    except ValueError as e:
        raise HTTPException(status_code=401,detail=str(e))

@router.get("/user",response_model=UserModelResponse)
async def read_token(
        user: User=Depends(verify_token),
):
    try:
        return user
    except ValueError as e:
        raise HTTPException(status_code=401,detail=str(e))

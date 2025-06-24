# core/utils/auth_utils.py
import uuid
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.models.auth_token import AuthToken
from core.models.user import User
from fastapi.security import APIKeyHeader

class TokenUtils:
    def __init__(self, session_factory):

        self.session_factory = session_factory
        self.api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

    async def verify_token(self, access_token_code: str = Depends(lambda: APIKeyHeader(name="Authorization", auto_error=True))) -> User:

        async with self.session_factory() as session:

            token = access_token_code.replace('Bearer ', '', 1) if access_token_code.startswith(
                'Bearer ') else access_token_code
            result = await session.execute(
                select(AuthToken).filter(AuthToken.access_token == token)
            )
            auth_token = result.scalar_one_or_none()

            if not auth_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Перевіряємо, чи є користувач, пов’язаний із токеном
            result = await session.execute(
                select(User).filter(User.id == auth_token.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User associated with token not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

    async def add_access_token(self, login: str, password: str) -> AuthToken:

        async with self.session_factory() as session:
            result = await session.execute(
                select(User).filter(User.login == login, User.password == password)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect login or password",
                )

            auth_token = AuthToken(
                access_token=str(uuid.uuid4()),
                user_id=user.id
            )
            session.add(auth_token)

            await session.commit()
            await session.refresh(auth_token)

            return auth_token
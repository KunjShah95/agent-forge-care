from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        return jwt.encode(
            {"sub": user_id, "exp": expire, "type": "access"},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        return jwt.encode(
            {"sub": user_id, "exp": expire, "type": "refresh"},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

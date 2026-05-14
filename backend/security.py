from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
import re
import hashlib
import os

SECRET_KEY = os.getenv("SECRET_KEY", "DEV_ONLY_SECRET_KEY_CHANGE_ME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

PASSWORD_POLICY_MESSAGE = (
    "Şifre en az 8 karakter olmalı; 1 büyük harf, 1 küçük harf, 1 rakam "
    "ve 1 özel karakter içermelidir."
)

PASSWORD_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$"


def is_password_strong(password: str) -> bool:
    return bool(re.match(PASSWORD_PATTERN, password))


def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        password = hashlib.sha256(password_bytes).hexdigest()

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")

    if len(password_bytes) > 72:
        plain_password = hashlib.sha256(password_bytes).hexdigest()

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
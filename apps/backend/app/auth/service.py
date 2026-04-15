from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import settings


def create_session_token(user_data: dict, keycloak_refresh_token: str = None) -> str:
    """Create backend session JWT"""
    expire = datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS)
    payload = {
        "sub": user_data.get("sub"),
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "roles": user_data.get("roles", []),
        "exp": expire,
    }

    if keycloak_refresh_token:
        payload["kc_refresh_token"] = keycloak_refresh_token

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_session_token(token: str) -> dict:
    """Verify and decode backend session JWT"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

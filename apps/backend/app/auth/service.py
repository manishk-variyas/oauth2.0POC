from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import settings


# Session management using JWT tokens instead of Redis sessions
#Flow:
# 1 - Create JWT token with user data and optional keycloack refresh token
# 2 - Verify and decode JWT token to get user data and refresh token

def create_session_token(user_data: dict, keycloak_refresh_token: str = None) -> str:
    """Create backend session JWT"""
    # Set Token expiration time (default to 24 hours) from now (current time + expire hours)
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

    # Encode / sign the jwt token with the secret key and algo defined in settings
    # Returns a string token used for auth in backend session management
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Verify and decode JWT token to get user data and refresh token
#Flow:
# 1 - Get JWT token from cookie
# 2 - Decode and verify the token using the secret key and algo defined in settings
# 3 - If valid, return the payload (user data + refresh token)

def verify_session_token(token: str) -> dict:
    """Verify and decode backend session JWT"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

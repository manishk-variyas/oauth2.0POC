from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError
from app.config import settings


def get_current_user(request: Request) -> dict:
    """Get current user from session cookie"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "sub": payload.get("sub"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }

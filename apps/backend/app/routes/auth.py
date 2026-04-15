import secrets
import hashlib
import base64
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
from jose import jwt, JWTError
from app.config import settings
from app.auth.service import create_session_token
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_pkce() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return code_verifier, code_challenge


def get_user_info_from_token(access_token: str) -> dict:
    try:
        payload = jwt.get_unverified_claims(access_token)
        return {
            "sub": payload.get("sub"),
            "username": payload.get("preferred_username"),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", []),
        }
    except Exception as e:
        logger.error(f"Error extracting user info: {e}")
        return {}


async def refresh_keycloak_token(refresh_token: str) -> dict:
    token_url = (
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to refresh Keycloak token")

    return response.json()


@router.get("/login")
async def login(request: Request):
    state = generate_state()
    code_verifier, code_challenge = generate_pkce()

    request.session["oauth_state"] = state
    request.session["code_verifier"] = code_verifier

    auth_url = (
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/auth"
    )
    params = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "redirect_uri": f"{settings.BACKEND_URL}/auth/callback",
        "response_type": "code",
        "scope": "openid profile email offline_access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(url=f"{auth_url}?{query_string}")


@router.get("/callback")
async def callback(code: str, state: str, request: Request):
    saved_state = request.session.get("oauth_state")
    if not saved_state or saved_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    code_verifier = request.session.pop("code_verifier", None)
    request.session.pop("oauth_state", None)

    token_url = (
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.BACKEND_URL}/auth/callback",
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    tokens = response.json()
    user_data = get_user_info_from_token(tokens.get("access_token"))
    session_token = create_session_token(user_data, tokens.get("refresh_token"))

    redirect_response = RedirectResponse(url=f"{settings.FRONTEND_URL}/callback")
    redirect_response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
        path="/",
    )
    return redirect_response


@router.post("/refresh")
async def refresh_session(
    request: Request, current_user: dict = Depends(get_current_user)
):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="No session")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

    refresh_token = payload.get("kc_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token available")

    try:
        new_tokens = await refresh_keycloak_token(refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=401, detail="Session expired, please login again"
        )

    user_data = {
        "sub": payload.get("sub"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }

    new_session_token = create_session_token(user_data, new_tokens.get("refresh_token"))

    response = JSONResponse({"message": "Session refreshed", "user": user_data})
    response.set_cookie(
        key="session_token",
        value=new_session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
        path="/",
    )
    return response


@router.post("/logout")
@router.get("/logout")
async def logout():
    redirect_response = RedirectResponse(url=f"{settings.FRONTEND_URL}/login")
    redirect_response.delete_cookie("session_token")
    return redirect_response

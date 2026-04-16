import secrets
import hashlib
import base64
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
from jose import jwt, JWTError
from app.config import settings
from app.auth.redis_service import (
    create_session,
    get_session,
    refresh_session,
    delete_session,
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


## Utility function which generates a random string 
## That proves we started the login 
def generate_state() -> str:
    return secrets.token_urlsafe(32)


## Step 2 - Generate PKCE (Proof Key for Code Exchange)
## - Creates Two string -> a secret and its fingerprint
## If someone steals the login code they can't use it without the secret

def generate_pkce() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return code_verifier, code_challenge



## Extract the user info from keycloack's token 
## Why - The Access token contains who the user is (sub,username,email,roles)

def get_user_info_from_token(access_token: str) -> dict:
    try:
        ## Get the claims payload from jwt token
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

## Refresh the keycloack token
## What - > Get new access token using refresh token
## why - Access token expires 5 minutes , refresh token keeps user logged in 
## How - Send refresh token to keycloack , get new access + refresh token
async def refresh_keycloak_token(refresh_token: str) -> dict:
    token_url = (
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token"
    )

## Post request to keycloack with refresh token and client creds to get new tokens
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

    # If keycloack says no , raise error
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to refresh Keycloak token")

    # return new tokens (access+refresh)
    return response.json()


# Step - 5 - Revoke Keycloack token
## What - Tell keycloack to invalidate the refresh token 
## Why - During logout - we want to fully logout from keycloack too
## How - Send the refresh token to the keycloack logout endpoint to revoke(remove the token)
async def revoke_keycloak_token(refresh_token: str) -> bool:
    """Revoke refresh token at Keycloak for proper logout"""
    revoke_url = f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/logout"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            revoke_url,
            data={
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code in [200, 204]:
        logger.info("Keycloak token revoked successfully")
        return True
    else:
        logger.warning(
            f"Failed to revoke Keycloak token: {response.status_code} - {response.text}"
        )
        return False



@router.get("/login")
# What - start the login process
# Flow:
# 1 - Generate random state(CSRf Protection)
# 2 - Generate PKCE Code verified + code_challenge
# 3 - Save state + code_verifier in session (redis)
# 4 - Redirect to keycloack with params(client_id,redirect_uri,response_type,scope,state,code_challenge,code_challenge_method)
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
# What - Handle the callback from keycloack after user logs in
# Flow:
# 1 - Get code + state from query params
# 2 - Verify state with session (CSRF Protection)
# 3 - Get code_verifier from session
# 4 - Exchange code for tokens (access + refresh) by calling keycloack
# 5 - Extract user info from access token
# 6 - Create session in redis with user info + refresh token
# 7 - Set session_id cookie and redirect to frontend

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
    session_id = await create_session(user_data, tokens.get("refresh_token"))

    redirect_response = RedirectResponse(url=f"{settings.FRONTEND_URL}/callback")
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
        path="/",
    )
    return redirect_response


@router.post("/refresh")
# What - Refresh the user session using the refresh token
# Flow:
# 1 - Get session_id from cookie
# 2 - Get session data from redis using session_id
# 3 - Get refresh token from session data
# 4 - Call keycloack to get new tokens using refresh token
# 5 - Update session in redis with new refresh token and user info

async def refresh_session_endpoint(
    request: Request, current_user: dict = Depends(get_current_user)
):
    old_session_id = request.cookies.get("session_id")
    if not old_session_id:
        raise HTTPException(status_code=401, detail="No session")

    session_data = await get_session(old_session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session not found")

    refresh_token = session_data.get("kc_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token available")

    try:
        new_tokens = await refresh_keycloak_token(refresh_token)
    except HTTPException:
        await delete_session(old_session_id)
        raise HTTPException(
            status_code=401, detail="Session expired, please login again"
        )

    user_data = {
        "sub": session_data.get("sub"),
        "username": session_data.get("username"),
        "email": session_data.get("email"),
        "roles": session_data.get("roles", []),
    }

    new_session_id = await create_session(user_data, new_tokens.get("refresh_token"))

    await delete_session(old_session_id)

    response = JSONResponse({"message": "Session refreshed", "user": user_data})
    response.set_cookie(
        key="session_id",
        value=new_session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
        path="/",
    )
    return response


@router.post("/logout")
@router.get("/logout")
# What - Logout the user
# Flow:
# 1 - Get session_id from cookie
# 2 - Get session data from redis using session_id
# 3 - Get refresh token from session data
# 4 - Call keycloack to revoke the refresh token
# 5 - Delete session from redis
# 6 - Delete session_id cookie and redirect to login page

async def logout(request: Request):
    session_id = request.cookies.get("session_id")

    if session_id:
        session_data = await get_session(session_id)

        if session_data:
            refresh_token = session_data.get("kc_refresh_token")
            if refresh_token:
                await revoke_keycloak_token(refresh_token)

        await delete_session(session_id)

    redirect_response = RedirectResponse(url=f"{settings.FRONTEND_URL}/login")
    redirect_response.delete_cookie("session_id")
    return redirect_response

# Authentication System Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Auth Flow Diagram](#auth-flow-diagram)
3. [Keycloak Setup](#keycloak-setup)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (React)                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                │
│  │   Login     │───▶│  Callback    │───▶│    Home     │                │
│  │  (redirect) │    │ (verify auth)│    │ (api calls) │                │
│  └─────────────┘    └──────────────┘    └─────────────┘                │
│         │                    │                     │                    │
│         │     session_id cookie                with cookie             │
│         ▼                    ▼                     ▼                    │
└─────────────────────────────────────────────────────────────────────────┘
           │                    │                     │
           ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
│  ┌──────────────────┐    ┌──────────────────────┐    ┌──────────────┐ │
│  │ SessionMiddleware│    │  /auth/callback      │    │  /api/*      │ │
│  │ (oauth state +   │    │  (create Redis       │    │  (verify      │ │
│  │  code_verifier)  │    │   session)           │    │   Redis)      │ │
│  └──────────────────┘    └──────────────────────┘    └──────────────┘ │
│                                    │                                     │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              REDIS                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  session:{session_id} = {sub, username, email, roles,             │ │
│  │                         kc_refresh_token}                          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         KEYCLOAK (OIDC Provider)                        │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                │
│  │   Login     │◀───│  Auth Code   │───▶│   Token     │                │
│  │  Page       │    │   Exchange   │    │   Refresh   │                │
│  └─────────────┘    └──────────────┘    └─────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Auth Flow Diagram (Mermaid)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Redis
    participant Keycloak

    Note over User, Frontend: User clicks "Login"
    Frontend->>Backend: GET /auth/login
    Note over Backend: Generate state + PKCE
    Backend->>Keycloak: Redirect with state parameter
    
    Note over User, Keycloak: User enters credentials
    Keycloak->>Frontend: Redirect with auth code
    
    Frontend->>Backend: GET /auth/callback?code=XXX&state=YYY
    Note over Backend: Validate state from session cookie
    Backend->>Keycloak: Exchange code for tokens
    Keycloak->>Backend: access_token + refresh_token
    
    Note over Backend: Store session in Redis
    Backend->>Redis: SET session:{id} = {user_data, refresh_token}
    Backend->>Frontend: Set-Cookie: session_id={id}, redirect to /callback
    
    Frontend->>Backend: GET /api/me (with session_id cookie)
    Backend->>Redis: GET session:{id}
    Redis->>Backend: {user_data}
    Backend->>Frontend: Return user data
    
    Note over Frontend, User: User sees dashboard
    
    Note over User, Backend: Session expires / needs refresh
    Frontend->>Backend: POST /auth/refresh (with session_id cookie)
    Backend->>Redis: GET session:{id} -> get refresh_token
    Backend->>Keycloak: Refresh token
    Keycloak->>Backend: New tokens
    Backend->>Redis: UPDATE session with new refresh_token
    Backend->>Frontend: Success response
```

---

# KEYCLOAK SETUP - STEP BY STEP

## Step 1: Start Keycloak

### Using Docker Compose
```bash
cd infra
docker-compose up -d
```

### Verify Keycloak is Running
- Open browser: http://localhost:8080
- You should see Keycloak login page

---

## Step 2: Login to Keycloak Admin Console

1. **Open**: http://localhost:8080/admin/
2. **Login** with default admin credentials:
   - Username: `admin`
   - Password: `admin`
3. After login, you'll see the **Master** realm (default realm)

---

## Step 3: Create a New Realm

### What is a Realm?
A realm is like a separate namespace - it contains users, clients, and configuration. Each application should have its own realm.

### Steps:
1. Click on the **Master** dropdown (top-left corner)
2. Click **Add realm**
3. Fill in:
   - **Name**: `notes-app` (or your app name)
4. Click **Create**

### Result:
- You should now see `notes-app` in the realm dropdown
- The realm is now active

---

## Step 4: Create a Client

### What is a Client?
A client represents an application that needs to authenticate with Keycloak. For our case, we have two:
1. **Frontend** (React app) - for user login
2. **Backend** (FastAPI) - for token exchange

### Steps to Create:
1. In the left sidebar, click **Clients**
2. Click **Create client** (top-right button)
3. Fill in the form:

| Field | Value | Description |
|-------|-------|-------------|
| Client ID | `notes-app-client` | Unique identifier for your client |
| Name | Notes App Client | Display name |
| Description | Notes application frontend | Optional description |

4. Click **Next**
5. On the next screen, configure:

| Field | Value | Description |
|-------|-------|-------------|
| Client authentication | OFF (Public) | We'll use authorization code flow |
| Authorization | OFF | Standard flow enabled |
| Authentication | ON | Standard OAuth2 flow |
| Direct access grants | ON | Allow password grant (for testing) |

6. Click **Save**

### Configure Client Settings:
After creating, you'll see client details. Configure these tabs:

#### a) General Settings (keep defaults)
- Client ID: `notes-app-client`
- Name: Notes App Client

#### b) Valid Redirect URIs (IMPORTANT!)
This is where Keycloak will redirect after login. Add:

```
http://localhost:5173/*
http://localhost:5173/callback
http://localhost:8000/*
http://localhost:8000/auth/callback
```

**How to add:**
1. Go to **Valid Redirect URIs** field
2. Add each URL on a new line
3. The `*` wildcard allows any path under that URL

#### c) Web Origins
Add these to allow CORS from frontend:

```
http://localhost:5173
http://localhost:8000
```

#### d) Client Settings (Important Flags)
Ensure these are enabled:
- ✅ **Standard flow enabled** - For OAuth2 authorization code flow
- ✅ **Direct access grants enabled** - For testing with password flow
- ✅ **Implicit flow enabled** - OFF (we don't need it)
- ✅ **Service accounts enabled** - OFF (not needed)
- ✅ **Public client** - ON (for frontend)

### Save Client
Click **Save** after configuring.

---

## Step 5: Get Client Credentials (For Confidential Clients)

If you set Client authentication to ON (confidential), you'll need the secret:

1. Go to your client (`notes-app-client`)
2. Click on the **Credentials** tab
3. Copy the **Client secret** value

> ⚠️ **Note**: We used "Public" client type, so no secret needed. But if you use "Confidential", you'll need this secret.

---

## Step 6: Create Users

### What is a User?
A user is someone who can login to your application.

### Steps:
1. In left sidebar, click **Users**
2. Click **Add user** (top-right)
3. Fill in user details:

| Field | Value | Description |
|-------|-------|-------------|
| Username | `testuser` | Login username |
| Email | testuser@example.com | User email |
| First Name | Test | First name |
| Last Name | User | Last name |
| Email verified | ON | Email is verified |
| User enabled | ON | User can login |

4. Click **Create**

### Set Password:
After creating user:
1. Go to the **Credentials** tab
2. Enter password: `password123`
3. Set **Temporary** to `OFF` (so user doesn't have to change on first login)
4. Click **Set Password**

---

## Step 7: Configure Client Scopes (Optional)

Client scopes define what information (claims) is included in the token.

### Default Scopes:
Keycloak automatically includes these scopes. You can see them in:
1. Go to **Client scopes** in left sidebar
2. Click on `notes-app-client-dedicated`

Default scopes include:
- profile (name, picture, etc.)
- email (email address)
- roles (user roles)

### Adding offline_access (For Refresh Tokens):
1. Go to your client **Client scopes** tab
2. Click **Add scope**
3. Search for `offline_access`
4. Check it and click **Add**

This allows getting a refresh token for session renewal.

---

## Step 8: Configure Realm Settings (Optional)

### Email Settings (for password reset):
If you want email features:
1. Go to **Realm settings** → **Email**
2. Configure SMTP server settings (for development, you can skip this)

---

## Step 9: Test Authentication

### Method 1: Using Keycloak Admin Console (Test Users)
1. Go to **Users**
2. Select a user
3. Click **Impersonate** (top-right)
4. This opens a new session as that user

### Method 2: Using OAuth2 Flow (Our Implementation)
1. Start your backend: `uvicorn app.main:app --port 8000`
2. Start your frontend: `npm run dev` (port 5173)
3. Go to http://localhost:5173
4. Click "Sign in with Keycloak"
5. Login with `testuser` / `password123`

### Method 3: Direct Access Grant (Testing)
```bash
curl -X POST http://localhost:8080/realms/notes-app/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=notes-app-client" \
  -d "username=testuser" \
  -d "password=password123"
```

---

## Keycloak Settings Summary

### Realm Settings to Verify:
| Setting | Value | Notes |
|---------|-------|-------|
| Enabled | ON | Realm is active |
| Login with email | OFF | Use username |
| Duplicate emails | OFF | Emails must be unique |

### Client Settings to Verify:
| Setting | Value | Notes |
|---------|-------|-------|
| Client ID | notes-app-client | Your client ID |
| Client Protocol | openid-connect | OIDC protocol |
| Access Type | public | No client secret needed |
| Standard Flow | ON | Authorization code flow |
| Direct Access Grants | ON | Password grant for testing |
| Valid Redirect URIs | See above | Your app URLs |
| Web Origins | See above | For CORS |

---

## Common Keycloak Configurations

### Configuration 1: Public Client (Frontend + Backend)
Use this when frontend is SPA (React/Vue):
- Access Type: **Public**
- Client authentication: **OFF**
- Valid Redirect URIs: Your frontend URLs

### Configuration 2: Confidential Client (Backend Only)
Use this for server-side OAuth:
- Access Type: **Confidential**
- Client authentication: **ON**
- Client secret: Copy from Credentials tab

---

## Keycloak URLs Reference

| URL | Purpose |
|-----|---------|
| `http://localhost:8080` | Keycloak base URL |
| `http://localhost:8080/admin/` | Admin console |
| `http://localhost:8080/realms/{realm-name}` | Realm endpoint |
| `http://localhost:8080/realms/{realm-name}/protocol/openid-connect/auth` | Authorization endpoint |
| `http://localhost:8080/realms/{realm-name}/protocol/openid-connect/token` | Token endpoint |
| `http://localhost:8080/realms/{realm-name}/protocol/openid-connect/logout` | Logout endpoint |
| `http://localhost:8080/realms/{realm-name}/protocol/openid-connect/certs` | JWKS endpoint |

---

# BACKEND IMPLEMENTATION

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app setup (~40 lines)
│   ├── config.py            # All settings in one place
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── dependencies.py  # get_current_user dependency
│   │   └── service.py       # Token creation/verification
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # /auth/* endpoints
│   │   └── notes.py         # /api/notes endpoints
│   ├── db.py               # Database connection
│   ├── schema.py           # Pydantic models
│   └── models.py           # SQLAlchemy models
└── .env                    # Environment variables
```

---

## Environment Variables (.env)

```bash
# Keycloak
KEYCLOAK_URL=http://localhost:8080
REALM=notes-app
KEYCLOAK_CLIENT_ID=notes-app-client
KEYCLOAK_CLIENT_SECRET=xvbAvMEWemYMwSPr6YSzjdRGG706wyCC

# Session / JWT
SECRET_KEY=cd81bb7fcea33bcd69352b5da53aa36590cb71aa140e34af8b91025749ac9b02
ALGORITHM=HS256
SESSION_EXPIRE_HOURS=24

# URLs
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# Cookie
COOKIE_SECURE=false  # true in production with HTTPS

# Database
DATABASE_URL=postgresql://notes:notes123@localhost:5432/notes

# Redis (for session storage)
REDIS_URL=redis://localhost:6379
```

**Generate your own SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Key Backend Files

### config.py - Centralized Settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8080"
    REALM: str = "notes-app"
    KEYCLOAK_CLIENT_ID: str = "notes-app-client"
    KEYCLOAK_CLIENT_SECRET: str = "xvbAvMEWemYMwSPr6YSzjdRGG706wyCC"

    # Session / JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    SESSION_EXPIRE_HOURS: int = 24

    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Cookie
    COOKIE_SECURE: bool = False

    # Database
    DATABASE_URL: str = "postgresql://notes:notes123@localhost:5432/notes"

    # Redis (for session storage)
    REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### auth/dependencies.py - Get Current User (Redis-based)

```python
from fastapi import Request, HTTPException, Depends
from app.auth.redis_service import get_session


async def get_current_user(request: Request) -> dict:
    """Get current user from session cookie"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "sub": session_data.get("sub"),
        "username": session_data.get("username"),
        "email": session_data.get("email"),
        "roles": session_data.get("roles", []),
    }
```

---

### auth/redis_service.py - Redis Session Management

```python
import secrets
import json
from typing import Optional
import redis.asyncio as redis
from app.config import settings

redis_client = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def create_session(
    user_data: dict, keycloak_refresh_token: str = None, expires_hours: int = None
) -> str:
    """Create a new session in Redis and return session ID"""
    session_id = generate_session_id()
    expire_hours = expires_hours or settings.SESSION_EXPIRE_HOURS

    session_data = {
        "sub": user_data.get("sub"),
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "roles": user_data.get("roles", []),
    }

    if keycloak_refresh_token:
        session_data["kc_refresh_token"] = keycloak_refresh_token

    r = await get_redis()
    await r.set(
        _session_key(session_id), json.dumps(session_data), ex=expire_hours * 3600
    )

    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    """Get session data from Redis"""
    r = await get_redis()
    data = await r.get(_session_key(session_id))
    if data:
        return json.loads(data)
    return None


async def refresh_session(session_id: str, keycloak_refresh_token: str) -> bool:
    """Update session with new Keycloak refresh token"""
    r = await get_redis()
    data = await r.get(_session_key(session_id))
    if not data:
        return False

    session_data = json.loads(data)
    session_data["kc_refresh_token"] = keycloak_refresh_token

    await r.set(_session_key(session_id), json.dumps(session_data))
    return True


async def delete_session(session_id: str) -> bool:
    """Delete session from Redis (logout)"""
    r = await get_redis()
    result = await r.delete(_session_key(session_id))
    return result > 0
```

---

### routes/auth.py - Auth Endpoints (Redis-based)

```python
import secrets
import hashlib
import base64
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
from jose import jwt
from app.config import settings
from app.auth.redis_service import (
    create_session,
    get_session,
    refresh_session as redis_refresh_session,
    delete_session,
)
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
async def refresh_session_endpoint(
    request: Request, current_user: dict = Depends(get_current_user)
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session not found")

    refresh_token = session_data.get("kc_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token available")

    try:
        new_tokens = await refresh_keycloak_token(refresh_token)
    except HTTPException:
        await delete_session(session_id)
        raise HTTPException(
            status_code=401, detail="Session expired, please login again"
        )

    await redis_refresh_session(session_id, new_tokens.get("refresh_token"))

    user_data = {
        "sub": session_data.get("sub"),
        "username": session_data.get("username"),
        "email": session_data.get("email"),
        "roles": session_data.get("roles", []),
    }

    return JSONResponse({"message": "Session refreshed", "user": user_data})


async def revoke_keycloak_token(refresh_token: str) -> bool:
    """Revoke refresh token at Keycloak for proper logout"""
    revoke_url = (
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/logout"
    )

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
        logger.warning(f"Failed to revoke Keycloak token: {response.status_code}")
        return False


@router.post("/logout")
@router.get("/logout")
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
```

---

### routes/notes.py - Protected Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.dependencies import get_current_user
from app.schema import NoteCreate, NoteUpdate, NoteResponse, PublicNoteResponse
from app.notes_service import (
    create_note, get_user_notes, get_note_by_id,
    update_note, delete_note, get_public_notes,
)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/public", response_model=list[PublicNoteResponse])
def list_public_notes(db: Session = Depends(get_db)):
    notes = get_public_notes(db)
    return [PublicNoteResponse(
        id=n.id, title=n.title, content=n.content,
        author="Anonymous", created_at=n.created_at, updated_at=n.updated_at,
    ) for n in notes]


@router.post("", response_model=NoteResponse)
def create(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = create_note(db, note, current_user["sub"])
    return NoteResponse.model_validate(result)


@router.get("", response_model=list[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    notes = get_user_notes(db, current_user["sub"])
    return [NoteResponse.model_validate(n) if hasattr(n, "id") else n for n in notes]


@router.get("/{note_id}", response_model=NoteResponse)
def get_one(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
def update(
    note_id: int,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    result = update_note(db, note, note_update, current_user["sub"])
    if not result:
        raise HTTPException(status_code=403, detail="Not authorized")
    return NoteResponse.model_validate(result)


@router.delete("/{note_id}")
def delete(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    delete_note(db, note, current_user["sub"])
    return {"message": "Note deleted"}
```

---

### main.py - App Entry Point (with Redis lifespan)

```python
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.db import init_db
from app.routes import auth_router, notes_router
from app.auth.dependencies import get_current_user
from app.auth.redis_service import close_redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Notes API...")
    init_db()
    yield
    logger.info("Shutting down Notes API...")
    await close_redis()


app = FastAPI(title="Notes API", version="1.0", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=3600)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Notes API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(notes_router, prefix="/api")
```

---

# FRONTEND IMPLEMENTATION

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx              # Main app with AuthContext
│   ├── pages/
│   │   ├── Login.jsx       # Login page
│   │   ├── Callback.jsx     # OAuth callback handler
│   │   ├── Home.jsx         # Protected page
│   │   └── Public.jsx       # Public page
│   └── services/
│       ├── auth.js          # Auth API calls
│       └── notes.js         # Notes API calls
└── package.json
```

---

## services/auth.js

```javascript
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,  // Important for cookies
});

export const login = () => {
  window.location.href = `${API_URL}/auth/login`;
};

export const logout = async () => {
  try {
    await axios.post(`${API_URL}/auth/logout`, {}, { withCredentials: true });
  } finally {
    window.location.href = '/login';
  }
};

export const checkAuth = async () => {
  try {
    const { data } = await api.get('/api/me');
    return data;
  } catch {
    return null;
  }
};
```

---

## App.jsx - Auth Context with Session Refresh

```jsx
import { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Home from './pages/Home';
import Public from './pages/Public';
import Callback from './pages/Callback';
import { checkAuth, refreshSession, logout as authLogout } from './services/auth';

const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth().then((userData) => {
      setUser(userData);
      setLoading(false);
    });
  }, []);

  // Session refresh every 4 minutes (with session rotation!)
  useEffect(() => {
    if (!user) return;

    const REFRESH_INTERVAL = 4 * 60 * 1000; // 4 minutes

    const interval = setInterval(async () => {
      try {
        await refreshSession(); // Creates new session + rotates
        console.log('Session refreshed');
      } catch (error) {
        console.error('Session refresh failed:', error);
        setUser(null);
      }
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [user]);

  const logout = async () => {
    await authLogout();
    setUser(null);
  };

  if (loading) {
    return <div style={loadingStyle}>Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
          <Route path="/callback" element={<Callback />} />
          <Route path="/public" element={<Public />} />
          <Route path="/" element={user ? <Home /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

const loadingStyle = {
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: '100vh',
};

export default App;
```

---

## pages/Callback.jsx

```jsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Callback() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/', { replace: true });
  }, [navigate]);

  return (
    <div style={styles.container}>
      <div style={styles.spinner}></div>
      <p>Processing login...</p>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    flexDirection: 'column',
    gap: '20px',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #f3f3f3',
    borderTop: '3px solid #3498db',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
};

export default Callback;
```

---

## pages/Home.jsx

```jsx
import { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { getNotes, createNote, deleteNote } from '../services/notes';

function Home() {
  const { user, logout } = useAuth();
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getNotes().then((data) => {
      setNotes(data);
      setLoading(false);
    });
  }, []);

  const handleCreate = async (note) => {
    await createNote(note);
    const data = await getNotes();
    setNotes(data);
  };

  const handleDelete = async (id) => {
    await deleteNote(id);
    setNotes(notes.filter(n => n.id !== id));
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <header>
        <h1>Welcome, {user.username}</h1>
        <button onClick={logout}>Logout</button>
      </header>
      <main>
        {notes.map(note => (
          <div key={note.id}>
            <h3>{note.title}</h3>
            <p>{note.content}</p>
            <button onClick={() => handleDelete(note.id)}>Delete</button>
          </div>
        ))}
      </main>
    </div>
  );
}

export default Home;
```

---

# SECURITY BEST PRACTICES

## ✅ DO

1. **Use Authorization Code Flow with PKCE**
   - More secure than Implicit or Password flow
   - Tokens never exposed to browser

2. **Use CSRF Protection**
   - Always generate and validate `state` parameter
   - Prevents cross-site request forgery

3. **Use HttpOnly Cookies**
   - Prevents XSS attacks from stealing session_id
   - `httponly=True` in cookie settings
   - Cookie contains only session_id, NOT user data

4. **Use Redis for Session Storage**
   - Session data stored in Redis, not in cookie
   - Full logout (delete from Redis + revoke Keycloak token)
   - Can track active sessions

5. **Use Strong SECRET_KEY**
   - Generate using: `python3 -c "import secrets; print(secrets.token_hex(32))"`
   - Never commit to version control

6. **Use HTTPS in Production**
   - Set `COOKIE_SECURE=True`
   - Set `secure=True` in cookie settings

7. **Validate Redirect URIs**
   - Only allow whitelisted redirect URLs
   - Prevents open redirect vulnerabilities

8. **Store Refresh Tokens in Redis**
   - Never in localStorage or exposed to client
   - Only backend has access via Redis

9. **Use Session Rotation on Refresh**
   - Session ID rotates every 4 minutes during refresh
   - Prevents session fixation attacks
   - Stolen cookies become useless after refresh

10. **Full Logout**
   - Revoke Keycloak refresh token
   - Delete session from Redis
   - Delete session cookie
   - User must re-login to Keycloak

## ❌ DON'T

1. **Don't Store Tokens in localStorage**
   - Vulnerable to XSS attacks
   - Use httpOnly cookies + Redis instead

2. **Don't Use Implicit Flow**
   - Tokens exposed in URL
   - No refresh tokens

3. **Don't Skip State Validation**
   - Always validate state in callback
   - Prevents CSRF attacks

4. **Don't Hardcode Secrets**
   - Use environment variables
   - Never commit secrets to git

5. **Don't Allow Any Redirect URI**
   - Whitelist specific URLs only
   - Prevents authorization code leakage

6. **Don't Store User Data in Cookie**
   - Cookie should only have session_id (random string)
   - User data stays in Redis
   - If cookie stolen, attacker still needs Redis access

---

# TROUBLESHOOTING

## Issue: "Invalid state parameter"
- **Cause**: CSRF validation failed
- **Fix**: 
  - Check SessionMiddleware is configured
  - Check state is being stored in session
  - Check state matches in callback

## Issue: "401 Unauthorized" on API calls
- **Cause**: Session cookie not being sent
- **Fix**: 
  - Check `withCredentials: true` in frontend axios
  - Check `httponly=True` cookie setting
  - Verify CORS allows credentials

## Issue: Infinite redirect loop
- **Cause**: Auth check failing, redirecting to login
- **Fix**: Callback page should NOT call checkAuth - just redirect

## Issue: "Failed to exchange code for token"
- **Cause**: Wrong redirect_uri or expired code
- **Fix**: 
  - Ensure redirect_uri matches Keycloak config exactly
  - Authorization code can only be used once

## Issue: Token refresh failing
- **Cause**: Refresh token expired or revoked
- **Fix**: User needs to re-login

## Issue: "Session not found" or "Invalid or expired session"
- **Cause**: Redis session doesn't exist (expired or deleted)
- **Fix**:
  - Check Redis is running: `redis-cli ping`
  - Check Redis connection in config
  - User needs to re-login

## Issue: Cannot connect to Redis
- **Cause**: Redis not running or wrong connection string
- **Fix**:
  - Start Redis: `redis-server`
  - Check REDIS_URL in .env matches your setup

---

# RUNNING THE APPLICATION

## 1. Start Redis (Required!)
```bash
redis-server
```

## 2. Start Keycloak
```bash
cd infra
docker-compose up -d
```

## 2. Start Backend
```bash
cd apps/backend
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

## 3. Start Frontend
```bash
cd apps/frontend
npm run dev
```

## 4. Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Keycloak Admin: http://localhost:8080/admin
- Keycloak Realm: http://localhost:8080/realms/notes-app
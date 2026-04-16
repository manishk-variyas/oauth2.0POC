import secrets
import json
from typing import Optional
from datetime import timedelta
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


# Session management functions
#Flow:
# 1 - Create session in redis with user data and optional keycloack refresh token
# 2 - Get session data from redis using session_id
# 3 - Update session with new keycloack refresh token
# 4 - Delete session from redis (logout)

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


# Update session with new Keycloak refresh token
#Flow:
# 1 - Get session data from redis using session_id
# 2 - Update session data with new keycloack refresh token

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


async def extend_session(session_id: str, hours: int = None) -> bool:
    """Extend session expiration time"""
    r = await get_redis()
    expire_hours = hours or settings.SESSION_EXPIRE_HOURS
    return await r.expire(_session_key(session_id), expire_hours * 3600)

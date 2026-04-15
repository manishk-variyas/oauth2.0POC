import redis
import json
from app.config import settings

# Create Redis connection
# decode_responses=True → returns string instead of bytes
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_jwks():
    # Try to get public keys from Redis cache first
    cached = redis_client.get("jwks:keys")

    if cached:
        # If found in cache → convert string to JSON and return
        return json.loads(cached)

    # If not found → fetch from Keycloak
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.JWKS_URL)
        response.raise_for_status()

        jwks = response.json()

        # Store in Redis for 1 hour (3600 seconds)
        # setex → set + expiry
        redis_client.setex("jwks:keys", 3600, json.dumps(jwks))

        return jwks


def get_cached_notes(user_id: str):
    # Try to get notes from Redis using user_id
    cached = redis_client.get(f"notes:{user_id}")

    if cached:
        # Convert JSON string back to Python object
        return json.loads(cached)

    # If not found → return None
    return None


def set_cached_notes(user_id: str, notes_json: str, expire: int = 300):
    # Store notes in Redis with expiry time (default 5 minutes)
    # Key format: notes:<user_id>
    redis_client.setex(f"notes:{user_id}", expire, notes_json)


def invalidate_cached_notes(user_id: str):
    # Delete cached notes when data changes (create/update/delete)
    redis_client.delete(f"notes:{user_id}")

#!/bin/bash
set -e

BASE_URL="http://localhost:8080"
REALM="notes-app"
CLIENT_ID="notes-app-client"
ADMIN_USER="admin"
ADMIN_PASS="admin"

REACT_ORIGINS="${REACT_ORIGINS:-http://localhost:5173,http://localhost:3000}"
IFS=',' read -ra ORIGINS <<< "$REACT_ORIGINS"

REDIRECT_URIS=""
WEB_ORIGINS=""
for origin in "${ORIGINS[@]}"; do
  REDIRECT_URIS+="\"$origin/*\","
  WEB_ORIGINS+="\"$origin\","
done
REDIRECT_URIS="${REDIRECT_URIS%,}"
WEB_ORIGINS="${WEB_ORIGINS%,}"

echo "=== Keycloak Setup ==="

# Login to get admin token
echo "Logging in..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" = "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo "ERROR: Failed to get admin token. Is Keycloak running?"
  exit 1
fi

# Check if realm exists
EXISTING_REALM=$(curl -s "$BASE_URL/admin/realms/notes-app" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.realm // empty')

if [ "$EXISTING_REALM" = "notes-app" ]; then
  echo "Realm 'notes-app' already exists, skipping..."
else
  echo "Creating realm $REALM..."
  curl -s -X POST "$BASE_URL/admin/realms" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"realm\":\"$REALM\",\"enabled\":true,\"displayName\":\"Notes App\"}"
  echo "Done"
fi

# Check if client exists
EXISTING_CLIENT=$(curl -s "$BASE_URL/admin/realms/$REALM/clients?clientId=$CLIENT_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].clientId // empty')

if [ "$EXISTING_CLIENT" = "$CLIENT_ID" ]; then
  echo "Client '$CLIENT_ID' already exists, updating..."
  CLIENT_UUID=$(curl -s "$BASE_URL/admin/realms/$REALM/clients?clientId=$CLIENT_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')
  curl -s -X PUT "$BASE_URL/admin/realms/$REALM/clients/$CLIENT_UUID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"clientId\":\"$CLIENT_ID\",\"enabled\":true,\"publicClient\":true,\"redirectUris\":[$REDIRECT_URIS],\"webOrigins\":[$WEB_ORIGINS],\"standardFlowEnabled\":true,\"directAccessGrantsEnabled\":true}"
  echo "Done"
else
  echo "Creating client $CLIENT_ID..."
  curl -s -X POST "$BASE_URL/admin/realms/$REALM/clients" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"clientId\":\"$CLIENT_ID\",\"enabled\":true,\"publicClient\":true,\"redirectUris\":[$REDIRECT_URIS],\"webOrigins\":[$WEB_ORIGINS],\"standardFlowEnabled\":true,\"directAccessGrantsEnabled\":true}"
  echo "Done"
fi

# Create roles
echo "Creating roles..."
for role in admin editor viewer; do
  curl -s -X POST "$BASE_URL/admin/realms/$REALM/roles" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$role\"}" 2>/dev/null || true
done

# Create test user
EXISTING_USER=$(curl -s "$BASE_URL/admin/realms/$REALM/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0]')

if [ "$(echo "$EXISTING_USER" | jq -r '.username // empty')" = "testuser" ]; then
  echo "User 'testuser' already exists, updating password..."
  USER_ID=$(echo "$EXISTING_USER" | jq -r '.id')
else
  echo "Creating test user..."
  USER_ID=$(curl -s -X POST "$BASE_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","email":"testuser@example.com","enabled":true}' | jq -r '.id')
fi

curl -s -X PUT "$BASE_URL/admin/realms/$REALM/users/$USER_ID/reset-password" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"password","value":"test123","temporary":false}' > /dev/null
echo "Done"

echo ""
echo "=== Complete ==="
echo "Keycloak Admin: http://localhost:8080/admin"
echo "Login: admin / admin"
echo "Test user: testuser / test123"
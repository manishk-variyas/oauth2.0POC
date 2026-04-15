# Notes App - Full Stack with OAuth 2.0

A notes application with React frontend, FastAPI backend, and Keycloak authentication using OAuth 2.0 + PKCE + BFF pattern.

## Quick Start

```bash
# 1. Start all services (Keycloak, Postgres, Redis, Nginx)
cd infra
docker-compose up -d

# 2. Setup Keycloak (creates realm, client, user)
bash setup-keycloak.sh

# 3. Start frontend and backend
cd apps
pnpm install
turbo run dev
```

Then open http://localhost:5173 and login with:

```
Username: testuser
Password: test123
```

---

## What's Here?

```
/
├── apps/
│   ├── frontend/     # React SPA
│   └── backend/      # FastAPI
├── infra/
│   ├── docker-compose.yml   # Keycloak + Postgres + Redis
│   └── setup-keycloak.sh   # Auto-setup script
├── docs/
│   ├── auth-flow.md      # Auth flow explained
│   └── auth-guide.md     # Keycloak setup guide
└── README.md
```

---

## Architecture

```
User -> Frontend -> Backend -> Keycloak
                 (BFF)       (Auth Server)
```

The backend handles all OAuth flow - tokens never reach the browser.

---

## Detailed Setup

### Step 1: Start Infrastructure

```bash
cd infra
docker-compose up -d
```

This starts:
- Keycloak on http://localhost:8080
- PostgreSQL for Keycloak data
- PostgreSQL for notes app
- Redis for caching

Wait 30 seconds for Keycloak to start up.

---

### Step 2: Setup Keycloak

Run the setup script:

```bash
bash setup-keycloak.sh
```

This automatically:
1. Creates realm `notes-app`
2. Creates client `notes-app-client`
3. Creates roles: admin, editor, viewer
4. Creates test user: `testuser` / `test123`

Output:
```
=== Keycloak Setup ===
Login in... Done
Creating realm notes-app... Done
Creating client notes-app-client... Done
Creating roles... Done
Creating test user... Done

=== Complete ===
Keycloak Admin: http://localhost:8080/admin
Login: admin / admin
Test user: testuser / test123
```

---

### Step 3: Start the Apps

```bash
cd apps
pnpm install
turbo run dev
```

This starts:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

---

### Step 4: Use the App

1. Open http://localhost:5173
2. Click "Login with Keycloak"
3. Login with: `testuser` / `test123`
4. Accept the permissions
5. You're logged in!

---

## Manually Setting Up Keycloak (Optional)

If you want to do it yourself:

### 1. Open Keycloak Admin

Go to http://localhost:8080/admin
Login: admin / admin

### 2. Create Realm

- Click "Add realm"
- Name: `notes-app`

### 3. Create Client

- Go to Clients -> Create client
- Client ID: `notes-app-client`
- Client Protocol: openid-connect
- Client authentication: OFF (public client)
- Standard flow: ON
- Direct access grants: ON
- Valid Redirect URIs:
  ```
  http://localhost:5173/*
  http://localhost:8000/*
  ```
- Web Origins:
  ```
  http://localhost:5173
  http://localhost:8000
  ```

### 4. Create User

- Go to Users -> Add user
- Username: `testuser`
- Email: testuser@example.com
- User enabled: ON
- Go to Credentials tab -> Set password: `test123` (temporary: OFF)

---

## Testing the Auth Flow

### Test Login

```bash
# Get authorization code
curl "http://localhost:8080/realms/notes-app/protocol/openid-connect/auth?client_id=notes-app-client&redirect_uri=http://localhost:8000/auth/callback&response_type=code&scope=openid+profile+email&state=abc123"
```

Then open the URL in a browser, login, and you'll be redirected to the callback.

### Test Token Exchange

```bash
# Exchange code for tokens
curl -X POST "http://localhost:8080/realms/notes-app/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=notes-app-client" \
  -d "code=YOUR_CODE_HERE" \
  -d "redirect_uri=http://localhost:8000/auth/callback"
```

### Test API with Token

```bash
# Get user info
curl "http://localhost:8000/api/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Environment Variables

### Backend (.env)

The backend uses these defaults (already configured):

```
KEYCLOAK_URL=http://localhost:8080
REALM=notes-app
KEYCLOAK_CLIENT_ID=notes-app-client
KEYCLOAK_CLIENT_SECRET=
SECRET_KEY=change-in-production
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

---

## Ports

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React app |
| Backend | http://localhost:8000 | FastAPI |
| Keycloak | http://localhost:8080 | Auth server |
| Keycloak Admin | http://localhost:8080/admin | Admin console |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

---

## Common Issues

### "Failed to get admin token"

Keycloak isn't ready yet. Wait 30 seconds and try again.

### "Invalid state parameter"

Session expired or cookies blocked. Enable third-party cookies or use localhost.

### "401 Unauthorized"

- Check `withCredentials: true` in frontend
- Check CORS settings in backend

### Infinite redirect loop

The callback page shouldn't check auth. It's just a redirect page.

---

## Learning More

See these docs for deep dive:

- [docs/auth-flow.md](docs/auth-flow.md) - Full OAuth 2.0 flow explained
- [docs/auth-guide.md](docs/auth-guide.md) - Keycloak setup details
- [docs/demo-guide.md](docs/demo-guide.md) - Demo testing guide

---

## Tech Stack

- **Frontend**: React + Vite
- **Backend**: FastAPI + SQLAlchemy
- **Auth**: Keycloak (OAuth 2.0 + PKCE)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Proxy**: Nginx# oauth-2.0
# oauth2.0POC
# oauth2.0POC
# oauth2.0POC
# oauth2.0POC
# oauth2.0POC
# oauth2.0POC

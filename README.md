# 🛡️ CyberAuth — JWT + OAuth2 Auth System

Full-stack authentication service with a cyberpunk-themed React UI, FastAPI backend, PostgreSQL database.

## Stack
| Layer      | Tech                            |
|------------|---------------------------------|
| Frontend   | React 18 + Vite                 |
| Backend    | FastAPI (async)                 |
| Database   | PostgreSQL + SQLAlchemy async   |
| Auth       | JWT (access + refresh) + OAuth2 |
| Providers  | Google, GitHub                  |

---

## Project Structure

```
auth-system/
├── backend/
│   ├── main.py          ← FastAPI app (all routes)
│   ├── models.py        ← SQLAlchemy User model
│   ├── schemas.py       ← Pydantic request/response schemas
│   ├── database.py      ← Async DB engine + session
│   ├── config.py        ← Settings via .env
│   ├── requirements.txt
│   └── .env.example     ← Copy to .env and fill in
└── frontend/
    ├── src/
    │   ├── App.jsx      ← Main UI (login page + canvas)
    │   └── main.jsx
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## Quick Start

### 1. PostgreSQL Database
```bash
psql -U postgres
CREATE DATABASE cyberauth;
\q
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Then edit .env with your values
uvicorn main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                     # Runs on http://localhost:3000
```

---

## API Endpoints

| Method | Endpoint                   | Description                  | Auth |
|--------|----------------------------|------------------------------|------|
| POST   | `/auth/register`           | Create account (email+pass)  | ❌    |
| POST   | `/auth/login`              | Login → JWT tokens           | ❌    |
| POST   | `/auth/refresh`            | Refresh access token         | ❌    |
| GET    | `/auth/me`                 | Get current user             | ✅    |
| POST   | `/auth/logout`             | Logout (client-side)         | ✅    |
| GET    | `/auth/google`             | Start Google OAuth flow      | ❌    |
| GET    | `/auth/google/callback`    | Google OAuth callback        | ❌    |
| GET    | `/auth/github`             | Start GitHub OAuth flow      | ❌    |
| GET    | `/auth/github/callback`    | GitHub OAuth callback        | ❌    |
| GET    | `/health`                  | Health check                 | ❌    |

Interactive docs at: **http://localhost:8000/docs**

---

## Using the API in Other Projects

### Get a token
```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com&password=secret"
```

### Use the token
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### JavaScript / React
```js
// Login
const res = await fetch('http://your-server/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ username: email, password }),
});
const { access_token, refresh_token, user } = await res.json();

// Authenticated request
await fetch('http://your-server/auth/me', {
  headers: { Authorization: `Bearer ${access_token}` }
});
```

---

## OAuth Setup

### Google
1. Go to https://console.cloud.google.com
2. Create project → APIs & Services → Credentials
3. OAuth 2.0 Client ID → Web Application
4. Add `http://localhost:8000/auth/google/callback` to redirect URIs
5. Copy Client ID + Secret into `.env`

### GitHub
1. Go to https://github.com/settings/developers → New OAuth App
2. Homepage URL: `http://localhost:3000`
3. Callback URL: `http://localhost:8000/auth/github/callback`
4. Copy Client ID + Secret into `.env`

---

## Production Checklist
- [ ] Change `SECRET_KEY` to a random 64-char string
- [ ] Set `DATABASE_URL` to your production PostgreSQL
- [ ] Update `ALLOWED_ORIGINS` and `FRONTEND_URL`
- [ ] Update OAuth redirect URIs in Google/GitHub dashboards
- [ ] Use HTTPS everywhere
- [ ] Add Redis token blacklist for logout invalidation
- [ ] Run `uvicorn main:app --workers 4` or use Gunicorn

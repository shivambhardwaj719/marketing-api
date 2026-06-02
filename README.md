# FastFacebook CRM — Backend API

Production-grade FastAPI backend for a **Facebook Lead Ads CRM & Campaign Management** platform.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 + Python 3.12 |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache / Queue broker | Redis 7 |
| Background workers | Celery 5 |
| Auth | JWT (python-jose) + Facebook OAuth 2.0 |
| Facebook APIs | Graph API v21.0 + Marketing API + WhatsApp Cloud API |
| HTTP client | HTTPX (async) + Tenacity retries |
| Validation | Pydantic v2 |
| Containers | Docker + Docker Compose |

---

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Facebook Developer App with the required permissions

### 2. Environment setup

```bash
cp .env.example .env
# Edit .env — set FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, SECRET_KEY, JWT_SECRET_KEY
```

Generate a Fernet encryption key for storing tokens:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Paste the output as `ENCRYPTION_KEY` in `.env`.

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

Services:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Flower (Celery monitor): http://localhost:5555

### 4. Run locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis manually, then:
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 5. Run Celery workers

```bash
# Leads queue
celery -A app.workers.celery_app.celery_app worker -Q leads --loglevel=info

# Campaigns queue
celery -A app.workers.celery_app.celery_app worker -Q campaigns --loglevel=info
```

---

## Architecture

```
app/
├── api/v1/
│   ├── auth/          # Facebook OAuth, JWT tokens
│   ├── facebook/      # Pages, Ad Accounts, forms
│   ├── campaigns/     # CRUD + Facebook sync
│   ├── leads/         # Lead management, status updates
│   ├── analytics/     # Dashboard, CPL, performance
│   ├── webhooks/      # Facebook & WhatsApp webhooks
│   └── whatsapp/      # WhatsApp Campaigns, Templates, Messages
│
├── core/
│   ├── config.py      # Pydantic settings (env-based)
│   ├── database.py    # Async SQLAlchemy engine + session
│   ├── security.py    # JWT, Fernet encryption, password hashing
│   ├── middleware.py  # Request ID, exception handler, security headers
│   ├── exceptions.py  # Typed exception hierarchy
│   └── logger.py      # Structured logging (structlog)
│
├── models/            # SQLAlchemy ORM models
├── schemas/           # Pydantic v2 request/response schemas
├── repositories/      # Data-access layer (async queries)
├── services/          # Business logic layer
├── workers/           # Celery tasks (async via event loop)
└── integrations/
    ├── facebook/      # FacebookGraphClient (HTTPX + retries)
    └── whatsapp/      # WhatsAppCloudClient (Meta Cloud API)
```

### Request flow

```
Request → CORS → SecurityHeaders → RequestContext (request_id) → ExceptionHandler
→ Rate Limiter → Router → Dependency Injection (auth, db session)
→ Route Handler → Service → Repository → Database
```

---

## API Reference

### Authentication

```
GET  /api/v1/auth/facebook/login       — Get OAuth URL
GET  /api/v1/auth/facebook/callback    — OAuth callback (returns JWT)
POST /api/v1/auth/refresh              — Refresh access token
GET  /api/v1/auth/me                   — Current user profile
```

### Facebook Connections

```
GET  /api/v1/facebook/accounts                               — List connected FB accounts
POST /api/v1/facebook/accounts/{id}/sync-pages               — Sync Facebook pages
POST /api/v1/facebook/accounts/{id}/sync-ad-accounts         — Sync ad accounts
POST /api/v1/facebook/pages/{id}/subscribe-webhook           — Subscribe page to leadgen webhook
GET  /api/v1/facebook/pages/{id}/forms                       — List lead forms
```

### Campaigns

```
GET  /api/v1/campaigns                         — List campaigns (paginated)
POST /api/v1/campaigns/sync/{ad_account_id}    — Sync from Facebook
POST /api/v1/campaigns                         — Create campaign
GET  /api/v1/campaigns/{id}                    — Get campaign
PATCH /api/v1/campaigns/{id}                   — Update campaign
POST /api/v1/campaigns/{id}/pause              — Pause campaign
POST /api/v1/campaigns/{id}/resume             — Resume campaign
GET  /api/v1/campaigns/{id}/insights           — Performance insights
POST /api/v1/campaigns/{id}/sync-adsets        — Sync adsets
```

### Leads

```
GET  /api/v1/leads                       — List leads (paginated + filters)
GET  /api/v1/leads/{id}                  — Get single lead
PATCH /api/v1/leads/{id}/status          — Update lead status
POST /api/v1/leads/fetch-form-leads      — Bulk pull leads from a form
```

Query params for `GET /api/v1/leads`:
- `campaign_id`, `adset_id`, `form_id`, `page_fb_id`
- `status` (new/contacted/qualified/converted/lost)
- `search` (full-text on email, name, phone)
- `page`, `page_size`

### Analytics

```
GET /api/v1/analytics/dashboard                 — Full dashboard summary
GET /api/v1/analytics/leads/count              — Lead count with breakdowns
GET /api/v1/analytics/campaigns/performance    — Campaign performance table
```

### WhatsApp Campaigns

```
GET  /api/v1/whatsapp/templates                    — List approved templates
POST /api/v1/whatsapp/campaigns                    — Create WhatsApp campaign
GET  /api/v1/whatsapp/campaigns                    — List campaigns
GET  /api/v1/whatsapp/campaigns/{id}               — Get campaign details
POST /api/v1/whatsapp/campaigns/{id}/send          — Trigger campaign dispatch
POST /api/v1/whatsapp/messages/send                — Send single message
```

### Webhooks

```
GET  /api/v1/webhooks/facebook    — Webhook verification (hub.challenge)
POST /api/v1/webhooks/facebook    — Receive leadgen events
POST /api/v1/webhooks/whatsapp    — Receive message status updates
```

---

## Facebook Setup

### 1. Create a Facebook App

1. Go to https://developers.facebook.com/apps
2. Create a new app → **Business** type
3. Add products: **Facebook Login**, **Marketing API**, **Webhooks**

### 2. Required Permissions

```
ads_management
ads_read
business_management
leads_retrieval
pages_show_list
pages_read_engagement
email
public_profile
```

### 3. Configure OAuth Redirect URI

Set `https://yourdomain.com/api/v1/auth/facebook/callback` in:
App → Facebook Login → Settings → Valid OAuth Redirect URIs

### 4. Configure Webhook

- Callback URL: `https://yourdomain.com/api/v1/webhooks/facebook`
- Verify Token: value of `FACEBOOK_WEBHOOK_VERIFY_TOKEN` from `.env`
- Subscribe to: `leadgen`

### 5. WhatsApp Setup

1. In your Meta Developer App, add the **WhatsApp** product.
2. Setup a WhatsApp Business Account and generate an Access Token.
3. Configure the WhatsApp webhook URL: `https://yourdomain.com/api/v1/webhooks/whatsapp`
4. Subscribe to the `messages` webhook field.

---

## Database Schema

| Table | Purpose |
|---|---|
| `users` | SaaS users (authenticated via Facebook OAuth) |
| `facebook_accounts` | Connected FB user accounts (encrypted tokens) |
| `facebook_pages` | FB Pages owned by users |
| `ad_accounts` | FB Ad Accounts |
| `campaigns` | Campaigns synced/created via Marketing API |
| `adsets` | Ad sets per campaign |
| `ads` | Individual ads |
| `forms` | Lead gen forms per page |
| `leads` | Captured leads with full field data + status |
| `webhook_logs` | Audit log for all incoming webhooks |
| `whatsapp_campaigns`| WhatsApp bulk message campaigns |
| `whatsapp_messages` | Individual messages tracking delivery status |
| `whatsapp_templates`| Synced approved message templates |

### Run migrations

```bash
# Create a new migration (auto-detect from models)
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Security

- All Facebook tokens encrypted at rest with **Fernet** symmetric encryption
- JWT access tokens (60 min) + refresh tokens (30 days)
- Webhook payload signature verified with `sha256` HMAC
- CORS configured per environment
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`, HSTS in production
- Rate limiting: 60 req/min per IP (configurable)
- Input validation via Pydantic v2 on all endpoints

---

## Testing

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run a specific test
pytest tests/test_auth.py -v
```

---

## Sample Facebook API Requests (via curl)

### Exchange OAuth code for token

```bash
curl "https://graph.facebook.com/v21.0/oauth/access_token?client_id=APP_ID&client_secret=APP_SECRET&redirect_uri=REDIRECT_URI&code=CODE"
```

### Get user's pages

```bash
curl "https://graph.facebook.com/v21.0/me/accounts?fields=id,name,access_token&access_token=USER_TOKEN"
```

### Get campaigns for ad account

```bash
curl "https://graph.facebook.com/v21.0/act_AD_ACCOUNT_ID/campaigns?fields=id,name,status,objective&access_token=TOKEN"
```

### Get lead details

```bash
curl "https://graph.facebook.com/v21.0/LEAD_ID?fields=id,created_time,field_data,ad_id,form_id&access_token=PAGE_TOKEN"
```

### Get form leads

```bash
curl "https://graph.facebook.com/v21.0/FORM_ID/leads?fields=id,created_time,field_data&access_token=PAGE_TOKEN"
```

---

## Frontend Integration (React/Next.js)

```typescript
// 1. Get OAuth URL
const { data } = await api.get('/api/v1/auth/facebook/login');
window.location.href = data.oauth_url;

// 2. After callback, store tokens
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);

// 3. Use Bearer auth on all requests
axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

// 4. Auto-refresh on 401
axios.interceptors.response.use(null, async (error) => {
  if (error.response?.status === 401) {
    const { data } = await api.post('/api/v1/auth/refresh', {
      refresh_token: localStorage.getItem('refresh_token'),
    });
    // retry original request with new token
  }
});
```

---

## Environment Variables Reference

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | Yes |
| `REDIS_URL` | Redis URL | Yes |
| `SECRET_KEY` | App secret (min 32 chars) | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `ENCRYPTION_KEY` | Fernet key for token encryption | Yes |
| `FACEBOOK_APP_ID` | Facebook App ID | Yes |
| `FACEBOOK_APP_SECRET` | Facebook App Secret | Yes |
| `FACEBOOK_WEBHOOK_VERIFY_TOKEN` | Custom webhook verify token | Yes |
| `FACEBOOK_REDIRECT_URI` | OAuth callback URL | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta WhatsApp Phone Number ID | Yes (if using WA) |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Meta WhatsApp Business Account ID | Yes (if using WA) |
| `WHATSAPP_ACCESS_TOKEN` | System user token for WhatsApp API | Yes (if using WA) |
| `APP_ENV` | `development` or `production` | No |
| `DEBUG` | Enable SQL echo + debug logs | No |
| `RATE_LIMIT_PER_MINUTE` | Rate limit (default 60) | No |

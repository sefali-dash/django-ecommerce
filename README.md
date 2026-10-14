# E-Commerce REST API

Django REST Framework backend with JWT auth, catalog, cart, checkout, and admin endpoints.

## Requirements

- Python 3.9+ (3.12+ recommended)
- SQLite (default) or PostgreSQL

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
```

Use your email address when prompted; that account is a staff admin (`is_staff=True` after you confirm staff in createsuperuser, or set it in the shell).

## Run

```bash
python manage.py runserver
```

- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

## Authentication

Register:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","full_name":"Buyer","password":"StrongPass123"}'
```

Login:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","password":"StrongPass123"}'
```

Use the `access` token:

```bash
curl http://127.0.0.1:8000/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

Logout blacklists the refresh token you send. Access tokens stay valid until they expire.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

Registration and login are throttled (`auth`: 20/hour per IP or user).

## PostgreSQL

Set `DATABASE_URL` in `.env`, for example:

```
DATABASE_URL=postgres://user:password@localhost:5432/mini_ecommerce
```

Checkout uses `select_for_update()` inside `transaction.atomic()`. SQLite allows basic locking but is weak under heavy concurrent writes; use PostgreSQL in production.

## Catalog deletion

- Categories with products cannot be deleted (409).
- Products are soft-deleted (`is_active=False`) so past orders keep snapshots.

## Tests

```bash
python manage.py test
```

End-to-end coverage of all spec endpoints in one case:

```bash
python manage.py test accounts.tests.test_api_inventory
```

## API overview

| Access                        |  Count |
| ----------------------------- | -----: |
| Public (no access token)      |      9 |
| Public\* (refresh token only) |      1 |
| User (access token)           |     11 |
| Admin (staff + access token)  |     13 |
| **Total exercises**           | **34** |

Product search and category filter use `GET /api/products/?q=` and `GET /api/products/?category=`.

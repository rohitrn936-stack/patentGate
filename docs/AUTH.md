# Authentication & authorization

## Model

Stateless JWT (HS256) with two token types.

| Token   | Lifetime (default)        | Claims |
|---------|---------------------------|--------|
| access  | `ACCESS_TOKEN_EXPIRE_MINUTES` = 30 min | `sub`, `type="access"`, `ver`, `iat`, `exp`, `jti` |
| refresh | `REFRESH_TOKEN_EXPIRE_DAYS` = 14 days  | `sub`, `type="refresh"`, `ver`, `iat`, `exp`, `jti` |

- Passwords are hashed with **bcrypt** (`passlib`). Inputs over 72 bytes are
  rejected (bcrypt truncates silently); registration also requires ≥8 chars with
  a letter and a digit.
- `ver` is the user's `token_version`. `get_current_user` rejects a token whose
  `ver` doesn't match the row. `POST /api/auth/logout` increments
  `token_version`, which invalidates **every** outstanding access + refresh
  token for that user ("log out everywhere"; also the hook for password reset).
- Login returns the same generic `401 "Invalid email or password"` whether the
  account exists or the password is wrong.

## Endpoints

| Method & path              | Auth        | Purpose |
|----------------------------|-------------|---------|
| `POST /api/auth/register`  | none (5/min)| create user, return tokens |
| `POST /api/auth/login`     | none (10/min)| return tokens |
| `POST /api/auth/refresh`   | none (20/min)| exchange a refresh token for a new pair |
| `POST /api/auth/logout`    | access      | bump `token_version` (revoke all) |
| `GET  /api/auth/me`        | access      | current user |

## Enforcement

Every non-auth route depends on `get_current_user` (`app/dependencies/auth.py`),
which:

1. decodes the bearer token and checks `type == "access"`,
2. loads the user and checks `token_version`,
3. raises `401` (never `403`) on any failure, with a `WWW-Authenticate: Bearer`
   header; expired tokens get a distinct `"Token has expired"` message.

## Data isolation

Ownership is enforced in the query, not after the fetch:

```python
select(Product).where(Product.id == product_id, Product.user_id == current_user.id)
select(Analysis).join(Product).where(Analysis.id == id, Product.user_id == current_user.id)
```

A resource that exists but belongs to someone else returns **404**, not 403, so
the API never confirms the existence of another user's data. `create_analysis`
and `POST /{id}/run` re-check product ownership. This is covered by
`backend/tests/test_authorization.py`.

## Config guardrails

`app/config.py` refuses to start when `APP_ENV=production` and `JWT_SECRET` is
missing, a known placeholder, or shorter than 32 chars. In development it
substitutes a random **ephemeral** secret (with a warning) so the app still
boots — tokens then don't survive a restart.

## Known trade-off: frontend token storage

The Next.js client keeps the access + refresh tokens in `localStorage` and
auto-refreshes on `401`. This is simple but exposes tokens to XSS. The hardening
path is httpOnly, `SameSite=Strict`, `Secure` cookies set by the backend plus a
CSRF token for state-changing requests; the API is already structured to allow
that change without touching the agent or pipeline code.

## Rate limiting

`app/rate_limit.py` is a small in-process fixed-window limiter exposed as a
FastAPI dependency (`dependencies=[LOGIN_LIMIT]`). Per-IP, per-bucket. Set
`RATE_LIMIT_ENABLED=false` for tests, or put a shared store in front for a
multi-process deployment.

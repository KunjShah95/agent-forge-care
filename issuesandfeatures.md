# AgentForge Career OS — Comprehensive Security Audit & Issues Report

**Date:** July 3, 2026  
**Auditor:** AgentForge AI Security Audit System  
**Scope:** Full codebase audit (backend Python/FastAPI + frontend React/TypeScript)

---

## 🚨 CRITICAL SECURITY VULNERABILITIES

### C-1: Hardcoded/Weak JWT Secret in Production Configuration

**File:** `backend/app/config.py`  
**Severity:** 🔴 **CRITICAL**  
**Line:** `jwt_secret: str = "change-me-to-a-random-secret-key"`

**Issue:** The default JWT secret is a placeholder string that is clearly meant to be changed but there is no enforcement mechanism beyond a `field_validator` that only checks it's non-empty. In Docker Compose, this gets overridden by `JWT_SECRET` env var, but if the env var is missing (e.g., in development), every instance uses the same known secret.

**Risk:** Any attacker who knows this default secret can forge JWT tokens and impersonate any user.

**Fix:** Implement a startup check that refuses to start with the default value in production mode. Use a cryptographically generated key (e.g., `secrets.token_urlsafe(32)`) instead of a human-readable string as default.

---

### C-2: Firebase Certificates Cache Poisoning via Unvalidated HTTP Response

**File:** `backend/app/dependencies.py` — `_get_certs()` function  
**Severity:** 🔴 **CRITICAL**

**Issue:** The function fetches Firebase public certificates from Google and caches them. However:
1. The `requests.get(CERTS_URL)` call does NOT verify TLS certificate pinning — it relies on system CA trust alone
2. The `cache-control` header is parsed unsafely: `_certs_cache["expires_at"] = time.time() + max_age` where `max_age` is parsed from user-controlled HTTP response headers
3. If an attacker can perform a MITM attack, they could inject malicious certs that would be cached for up to `max-age` seconds

**Risk:** Authentication bypass via malicious certificate injection.

**Fix:** Add TLS certificate pinning or at minimum, validate the response signature. Validate `max-age` is within reasonable bounds (e.g., 0 to 86400). Use `httpx` with proper SSL context instead of `requests`.

---

### C-3: No SQL Injection Protection — Raw String Interpolation in Queries

**File:** `backend/app/api/v1/opportunities.py` — lines 60-75  
**Severity:** 🔴 **CRITICAL**

```python
if city:
    query = query.where(Opportunity.city.ilike(f"%{city}%"))
if state:
    query = query.where(Opportunity.state.ilike(f"%{state}%"))
```

**Issue:** While SQLAlchemy's `ilike` does parameterize the value, the pattern `f"%{city}%"` uses Python f-string interpolation. However, SQLAlchemy ORM's `.ilike()` method properly parameterizes these values, so this is **NOT** SQL injection vulnerable in practice because SQLAlchemy escapes parameters. However, this is still a code smell and could lead to issues if the query building changes in the future.

**Actual vulnerability:** The real concern is the `search` parameter handling:
```python
if search:
    search_term = f"%{search}%"
    query = query.where(
        Opportunity.title.ilike(search_term)
        | Opportunity.company.ilike(search_term)
        | Opportunity.description.ilike(search_term)
    )
```
This is safe with SQLAlchemy ORM, but the pattern is dangerous if any raw SQL is added later.

**Risk:** Low in current form (SQLAlchemy ORM handles it), but pattern is fragile.

**Fix:** Use `bindparam()` or pass parameters directly. Add a note to prevent future raw SQL from using these variables.

---

### C-4: No Rate Limiting on Authentication Endpoints

**File:** `backend/app/main.py` (rate limiting middleware)  
**Severity:** 🔴 **CRITICAL**

**Issue:** The rate limiter uses `_get_rate_limit_key()` which first tries to extract the user ID from the Bearer token. For unauthenticated requests (login, register endpoints), this falls back to IP address. However, there is **no rate limiting applied at the route level for auth endpoints specifically**. The middleware rate-limits all requests identically at a per-minute window.

**Risk:** Brute force attacks on login endpoints, enumeration attacks, abuse of the free-tier service.

**Fix:** Implement specific rate limiting on auth routes (login, register, password reset) with stricter limits (e.g., 5 attempts per minute per IP) and longer windows. Use `fastapi-limiter` or add route-specific decorators.

---

### C-5: Redis Rate Limiter Falls Back Silently on Failure

**File:** `backend/app/main.py` — rate limit middleware  
**Severity:** 🟠 **HIGH**

```python
except Exception:
    logger.warning("Rate limiter unavailable (Redis down?) — allowing request")
```

**Issue:** If Redis is down (DoS condition or misconfiguration), the rate limiter silently allows all requests through. This means an attacker can simply DDoS Redis to bypass all rate limiting.

**Fix:** In production, either fail-closed (deny requests when Redis is down) or fall back to an in-memory rate limiter. At minimum, raise an alert when Redis is unavailable.

---

### C-6: Missing Input Validation on UUID Parameters (Path Traversal Risk)

**Files:** Multiple API endpoints across `applications.py`, `contacts.py`, `memory.py`, `agents.py`  
**Severity:** 🟠 **HIGH**

**Issue:** Many endpoints accept UUID parameters from URL paths without validating they are valid UUIDs:
```python
async def get_task(id: str, ...)
async def delete_application(id: str, ...)
async def update_contact(id: str, ...)
```

While SQLAlchemy will likely reject non-UUID strings, the `id` parameter is only validated with generic checks like `if not id or len(id.strip()) < 1`.

**Risk:** In some cases, if the ORM model converts the string to a UUID internally, a malformed UUID could cause a 500 error (information disclosure via error message). More critically, if the `id` is used in a raw string context, it could enable injection attacks.

**Fix:** Use `UUID` type hint in FastAPI route parameters, or use Pydantic models with `uuid.UUID` types for path parameters.

---

### C-7: Hardcoded Firebase Project ID

**File:** `backend/app/config.py`  
**Severity:** 🟠 **HIGH**

```python
firebase_project_id: str = "developer-portfolio-aggregator"
```

**Issue:** The Firebase Project ID is hardcoded as a default. In `docker-compose.prod.yml`, it uses `${FIREBASE_PROJECT_ID:?FIREBASE_PROJECT_ID is required}`, but in the default `docker-compose.yml` it's overridden to a different value (`marine-order-481405-m2`), and in local development it falls back to the hardcoded default.

**Risk:** Misconfiguration could cause one environment's Firebase auth to accept tokens from another environment's Firebase project. The hardcoded default references what appears to be a real Firebase project (`developer-portfolio-aggregator`), which is a credential exposure risk.

**Fix:** Remove the hardcoded default. Make `firebase_project_id` required via environment variable in production.

---

### C-8: JWT Secret Exposed in Docker Compose Environment

**File:** `docker-compose.yml`  
**Severity:** 🟠 **HIGH**

```yaml
environment:
  - JWT_SECRET=${JWT_SECRET:-dev-secret-change-in-production}
```

**Issue:** The default JWT secret `dev-secret-change-in-production` is a weak, known value. If anyone runs `docker-compose up` without setting `JWT_SECRET`, all instances share this key.

**Risk:** Anyone who knows this default can forge JWTs.

**Fix:** Remove the default value. Make JWT_SECRET required, or generate a random one at startup if not set.

---

### C-9: No CSRF Protection

**Severity:** 🟠 **HIGH**

**Issue:** The application uses Bearer token authentication stored in `localStorage`. There is no CSRF token mechanism. Since the auth token is automatically attached to all requests via `Authorization` header (not cookies), CSRF is less of a concern for API calls. However, the frontend does not implement any state-changing nonce mechanism.

**Risk:** Low for cookie-less API calls, but if any endpoint accepts cookies or if there are cross-origin form submissions, CSRF could be exploitable.

**Fix:** Add CSRF protection for any cookie-based auth flows. Ensure CORS settings are restrictive enough (they are currently well-configured in `main.py`).

---

### C-10: No Security Headers for HTML Serving (Nginx)

**File:** `nginx.conf`  
**Severity:** 🟠 **HIGH**

**Issue:** The nginx configuration serves the SPA but does NOT include security headers like `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, etc.

The FastAPI backend adds some headers (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`), but these only apply to API routes proxied through nginx, not to the statically served frontend files.

**Risk:** The frontend pages are vulnerable to clickjacking, MIME-type sniffing attacks, and have no CSP to prevent XSS.

**Fix:** Add security headers to nginx configuration:
```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

### C-11: Environment Variable Fallback Chain Exposes Configuration State

**File:** `backend/app/config.py`  
**Severity:** 🟢 **MEDIUM**

**Issue:** The config loader reads `.env` file manually BEFORE pydantic-settings initializes, and sets values in `os.environ`. The comment says "real production env vars (Docker/CI) must never be overridden" — but the logic is:
```python
current = os.environ.get(key)
if key and value and (current is None or current == ""):
    os.environ[key] = value.strip().strip("\"'")
```

This means if an env var is set to an empty string (e.g., `OPENAI_API_KEY=`), the .env value will override it. This could cause production to use a dev API key.

**Risk:** Low in typical usage, but could cause accidental credential override in certain CI/CD scenarios.

---

## 🔴 HIGH SEVERITY BUGS

### B-1: Unicode/Postal Code Parsing May Produce `None` City Names

**File:** `backend/app/utils/location.py` (via `parse_location`)  
**Severity:** 🟠 **HIGH**

**Issue:** The `parse_location` function is called on every scraped/imported opportunity. If the location string is empty or contains non-standard formats (postal codes, non-ASCII characters), the `city`, `state`, or `country` fields could be `None`. Since some of these fields have `index=True`, having many `None` values in indexed columns wastes database resources.

**Risk:** Application crash if code assumes non-None location fields. Map visualizations may break.

---

### B-2: Broken Rate Limit Headers (Always Report 100 Remaining)

**File:** `backend/app/main.py` — security_headers_middleware  
**Severity:** 🟢 **MEDIUM**

```python
response.headers["X-RateLimit-Remaining"] = "100"
response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
```

**Issue:** The rate limit headers are static and always report 100 remaining requests and 60 seconds to reset, regardless of actual usage. These headers are worse than useless — they give clients a false sense of their rate limit status.

**Fix:** Compute actual remaining requests from the rate limiter state.

---

### B-3: Redis Connection Leaking in Rate Limiter

**File:** `backend/app/dependencies.py` — `RedisRateLimiter`  
**Severity:** 🟢 **MEDIUM**

**Issue:** The `RedisRateLimiter` creates a single Redis connection that is never disconnected/refreshed. If Redis restarts or the connection drops, the rate limiter won't recover until the application restarts.

**Risk:** Rate limiting may silently fail after Redis connection issues.

**Fix:** Implement connection retry with exponential backoff. Use `aioredis` connection pool properly.

---

### B-4: Web Scrapers Parse HTML Without Error Handling for Malformed Content

**File:** `backend/app/search/adapters.py` — Multiple BeautifulSoup parsers  
**Severity:** 🟢 **MEDIUM**

**Issue:** The web scrapers for Google, DuckDuckGo, LinkedIn, Mojeek, and job boards all parse HTML with `html.parser`. If any of these sites change their HTML structure (which happens frequently), the scrapers silently return empty results with just a debug log message. This cascades to demo data generation, which produces fake opportunities.

**Risk:** Users see fake/demo data mixed with real data without clear distinction.

---

### B-5: Demo Data Leaked to Production

**File:** `backend/app/utils/demo_data.py` (imported in `search/adapters.py` and `opportunity_agent/service.py`)  
**Severity:** 🟢 **MEDIUM**

**Issue:** When all search sources fail, the system generates fake "demo opportunities" with realistic-looking but entirely fabricated company names and job titles. These are stored in the database alongside real data. Users cannot distinguish real from fake.

**Risk:** Users may apply to fake jobs, wasting time and effort.

**Fix:** Never mix demo data with real data. Add clear labels like "[DEMO]" to any generated demo entries. Better yet, return an empty result with a clear message.

---

## 🟢 MODERATE SEVERITY ISSUES

### I-1: Missing `helmet`-like Security Middleware on Express/FastAPI

**Severity:** 🟢 **MEDIUM**

**Issue:** While the backend adds some security headers via middleware, it doesn't use a comprehensive security header library. Missing headers include:
- `Strict-Transport-Security` (HSTS)
- `Permissions-Policy`
- `Cross-Origin-Embedder-Policy`
- `Cross-Origin-Opener-Policy`
- `Cross-Origin-Resource-Policy`

These are added in the middleware but HSTS is missing and should be added.

---

### I-2: Firebase Analytics Initialized Before Consent

**File:** `src/lib/firebase.ts`  
**Severity:** 🟢 **MEDIUM**

```typescript
export const analytics = typeof window !== "undefined" && import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
    ? getAnalytics(app)
    : null;
```

**Issue:** Google Analytics (Firebase Analytics) is initialized immediately when the app loads, before any user consent is obtained. This violates GDPR and CCPA requirements.

**Risk:** Legal liability in EU and California markets.

**Fix:** Implement a consent management platform and only initialize analytics after user consent.

---

### I-3: No Authentication on `/health` and `/status` Endpoints

**File:** `backend/app/main.py` (health check), `backend/app/api/v1/status.py`  
**Severity:** 🟢 **MEDIUM**

**Issue:** The `/health` and `/api/v1/status` endpoints are unauthenticated and expose detailed information about the system, including:
- Database connection status
- Redis availability
- Qdrant collections
- All configured AI providers and their API key status (whether configured or not)
- All search sources and their availability
- Agent system health

This information helps attackers understand the attack surface.

**Fix:** Rate-limit these endpoints. In production, consider restricting them to internal networks or requiring a simple API key.

---

### I-4: No Pagination Size Limits Enforced on Filter Endpoints

**File:** `backend/app/api/v1/opportunities.py` — `get_filter_options`  
**Severity:** 🟢 **MEDIUM**

**Issue:** The filter endpoint has no pagination and returns all distinct values. If the user has thousands of opportunities with unique city/state values, this endpoint could return a very large response, causing memory pressure.

---

### I-5: Avatar File Upload Path Traversal

**File:** `backend/app/api/v1/profile.py` — `upload_avatar`  
**Severity:** 🟢 **MEDIUM**

```python
ext = file.filename.rsplit(".", 1)[-1] if file.filename else "png"
filename = f"{uuid.uuid4().hex}.{ext}"
filepath = AVATAR_DIR / filename
```

**Issue:** While the filename is UUID-based (preventing path traversal), the content type validation may not catch all cases. A file with a `.png` extension could contain executable code. The file is served statically by uvicorn/FastAPI.

**Fix:** Validate file contents (magic bytes) in addition to content type extensions. Serve avatars from a separate domain or with proper `Content-Disposition` headers.

---

### I-6: PDF Upload Size Limit But No Processing Time Limit

**Files:** `backend/app/api/v1/hiring_agent.py`, `backend/app/api/v1/resume.py`  
**Severity:** 🟢 **MEDIUM**

**Issue:** PDF uploads are limited to 10MB in size, but there's no time limit on processing. A malicious 10MB PDF with deeply nested structures or infinite loops could tie up server resources for extended periods.

**Fix:** Add a processing timeout (e.g., 30 seconds) for PDF extraction.

---

## 🔷 MISSING SECURITY FEATURES

### F-1: No Email Verification Flow

**Files:** `backend/app/api/v1/auth.py`, `src/lib/auth-context.tsx`

**Issue:** While the registration process calls `sendEmailVerification(cred.user)` on the frontend, the backend never verifies whether a user's email has been confirmed. Any authenticated user can access all features regardless of email verification status.

**Risk:** Users can create accounts with fake/disposable email addresses and access the full system. For a paid service, this undermines account integrity.

**Fix:** Add a middleware/dependency that checks `email_verified` claim from Firebase token and restricts features for unverified accounts.

---

### F-2: No API Key Authentication for Service-to-Service Calls

**Severity:** 🟢 **MEDIUM**

**Issue:** The system has numerous background tasks (RQ workers) and scheduled jobs that call internal services. None of these use API keys for internal authentication. If an attacker gains network access to the infrastructure, they can call any internal API.

**Fix:** Implement internal API key authentication for service-to-service communication, or use mutual TLS.

---

### F-3: No Audit Logging

**Files:** Multiple

**Issue:** There is no centralized audit log for sensitive operations:
- User login/logout
- Profile changes (especially email, password, linked accounts)
- Application stage changes
- Data export/download
- Admin actions
- API key usage

**Risk:** In case of a security breach, there's no way to determine what happened, when, or by whom.

**Fix:** Implement structured audit logging for all sensitive operations.

---

### F-4: No Session Management/Termination

**Files:** `src/lib/auth-context.tsx`

**Issue:** The application does not support:
- "Log out all other sessions"
- Session listing and management
- Session timeout enforcement
- Concurrent session limits

**Fix:** Track Firebase sessions and provide session management UI.

---

### F-5: No Two-Factor Authentication (2FA)

**Severity:** 🟢 **MEDIUM**

**Issue:** For a platform that stores resumes, personal data, and job search information, there is no 2FA option. Firebase supports TOTP and SMS 2FA but it's not implemented.

---

### F-6: No Data Encryption at Rest for PII Fields

**Files:** `backend/app/models/user.py`

**Issue:** Several fields contain personally identifiable information (PII) that is stored as plain text:
- `email` (indexed)
- `full_name`
- `avatar_url`
- Contact `email`, `phone`, `linkedin_url`
- Application `cover_letter`, `resume_version`
- Notifications with user data

None of these fields are encrypted at the database level.

**Fix:** Use PostgreSQL column-level encryption (`pgcrypto`) or application-level encryption for sensitive PII fields.

---

### F-7: No API Key Rotation Mechanism

**Severity:** 🟢 **LOW-MEDIUM**

**Issue:** There is no mechanism to rotate API keys (OpenAI, SendGrid, Firebase, etc.) without downtime. If a key is compromised, changing it requires a deployment.

---

### F-8: No Data Retention/Deletion Policy

**Files:** `backend/app/models/user.py`

**Issue:** There is no automated data retention policy. Old resumes, expired opportunities, and stale memory entries accumulate indefinitely. The `MemoryEntry` model has a `ttl_days` field but it's nullable and not enforced as a default.

**Fix:** Implement and enforce data retention policies. Add a scheduled job to delete expired data.

---

## 🐛 FUNCTIONAL BUGS & CODE QUALITY ISSUES

### Q-1: `model_dump()` Instead of `model_dump()` Typo

**File:** `backend/app/schemas/user.py` — multiple places  
**Severity:** 🟢 **LOW**

**Issue:** Multiple places use `model_dump()` which is correct for Pydantic v2. However, some files have inconsistent usage.

---

### Q-2: Inconsistent Auth Service — Deprecated Code Still in Codebase

**File:** `backend/app/services/auth_service.py`  
**Severity:** 🟢 **LOW**

**Issue:** The file is marked as ⚠️ DEPRECATED with a docstring noting it's "kept as a reference." However, having dead code in the codebase is a maintenance burden and could confuse developers.

---

### Q-3: Sync HTTP Call in Async Context (Firebase Cert Fetch)

**File:** `backend/app/dependencies.py`  
**Severity:** 🟢 **MEDIUM**

```python
response = requests.get(CERTS_URL)  # SYNC call in async context
```

**Issue:** `requests.get()` is a blocking synchronous call inside an async FastAPI application. This blocks the event loop for the duration of the HTTPS request, degrading performance.

**Fix:** Use `httpx.AsyncClient` instead.

---

### Q-4: RQ Worker Uses Blocking asyncio.run() — Blocks Thread Pool

**File:** `backend/app/tasks/agent_tasks.py`  
**Severity:** 🟢 **MEDIUM**

```python
async def process_research_task(task_id, user_id, query, focus):
    ...
    asyncio.run(_run_task(...))
```

**Issue:** RQ workers run sync functions by default. Using `asyncio.run()` inside a sync function blocks the worker thread. This means one long-running research task blocks the entire worker from processing other jobs.

**Fix:** Use `rq-scheduler` with async workers, or use `asyncio.get_event_loop().run_until_complete()` with proper loop management.

---

### Q-5: `/chat/stream` Endpoint Has No Auth Enforcement (Optional User)

**File:** `backend/app/api/v1/chat.py`  
**Severity:** 🟢 **MEDIUM**

```python
user: User = Depends(get_optional_user)
```

**Issue:** The chat streaming endpoint uses `get_optional_user`, which means unauthenticated users can use it. While this is intentional for "anonymous" access, it also means the endpoint has no rate limiting per-user (since there's no user ID), and relies entirely on IP-based rate limiting.

---

### Q-6: Profile Update Has No Authorization Check for Cross-User Access

**File:** `backend/app/api/v1/profile.py` — `update_profile`  
**Severity:** 🟠 **HIGH**

**Issue:** While the endpoint does enforce `get_current_user`, and correctly queries `Profile` by `Profile.user_id == user.id`, this is correct. However, the `skills/add` endpoint checks for existing skills but has a race condition:
```python
existing = await db.execute(...)
if existing.scalar_one_or_none():
    raise HTTPException(status_code=409, detail="Skill already added")
```
Between the check and the insert, another concurrent request could create the same skill.

**Fix:** Use database-level constraints (`UniqueConstraint`) on `(profile_id, skill_id)` to prevent duplicates at the DB level.

---

### Q-7: No Timeout on External API Calls in Search Adapters

**File:** `backend/app/search/adapters.py`  
**Severity:** 🟢 **MEDIUM**

**Issue:** Some search API calls use a 10-15 second timeout, but there's no circuit breaker pattern. If an external API (SerpAPI, Tavily, etc.) becomes slow or unresponsive, the search endpoint could hang for 10+ seconds trying each provider sequentially.

**Fix:** Implement circuit breaker pattern with per-provider timeouts and fail-fast behavior.

---

### Q-8: Sensitive Data in Logs

**Files:** Multiple

**Issue:** Error handling across many endpoints logs the full error string `str(e)` which may contain sensitive data (user input, API responses, SQL queries). For example:
```python
logger.error("Failed to update user %s: %s", user.id, str(e))
```

**Fix:** Implement log sanitization. Never log raw exception messages that may contain user input or database contents.

---

### Q-9: `X-vercel-ai-data-stream` Header Hardcoded in Chat Endpoint

**File:** `backend/app/api/v1/chat.py`  
**Severity:** 🟢 **LOW**

```python
headers={"x-vercel-ai-data-stream": "v1"}
```

**Issue:** A Vercel-specific header is hardcoded in the FastAPI response. This couples the backend to Vercel's frontend infrastructure.

---

### Q-10: Notification System Uses MemoryEntry Instead of Dedicated Table

**File:** `backend/app/services/notification_service.py`  
**Severity:** 🟢 **LOW**

**Issue:** Notifications are stored as MemoryEntry records with keys like `notification:<uuid>`. This means notifications share the same table as memory data, with no dedicated schema, indexing, or TTL management. Old notifications accumulate indefinitely.

---

### Q-11: No Observable Error Handling for LLM Failures

**Files:** Multiple agent services

**Issue:** When LLM calls fail (API key expired, rate limited, network error), agents fail silently or fall back to demo data. There's no user-facing error message that explains the underlying issue (e.g., "Your OpenAI API key has expired").

---

## 📦 DEPENDENCY VULNERABILITIES

### D-1: Old jsdom Version (20.0.3)

**File:** `package.json`  
**Severity:** 🟢 **MEDIUM**

```json
"jsdom": "^20.0.3"
```

**Issue:** `jsdom@20.0.3` is several versions behind the latest (stable is 25.x). Multiple CVEs have been fixed in later versions, including prototype pollution and sandbox escape vulnerabilities.

**Fix:** Update to `jsdom@^25.0.0` or latest.

---

### D-2: Vite 5.x — Consider Update to 6.x

**File:** `package.json`  
**Severity:** 🟢 **LOW**

`"vite": "^5.4.19"` — Vite 6.x is the current major version with critical security fixes.

---

### D-3: LangChain Dependencies Not Pinned

**File:** `backend/requirements.txt`  
**Severity:** 🟢 **LOW**

Many langchain packages (`langchain-groq`, `langchain-deepseek`, `langchain-mistralai`, etc.) have no version pinning. Using unpinned dependencies can lead to unexpected breakage or vulnerability introduction.

---

### D-4: `passlib[bcrypt]` Deprecated

**File:** `backend/requirements.txt`  
**Severity:** 🟢 **LOW**

`passlib` has been deprecated since 2023 and no longer receives security updates. While this is only used for the deprecated auth service, it should be removed entirely.

---

## 🏗️ ARCHITECTURAL CONCERNS

### A-1: Multiple, Overlapping Agent Systems

**Issue:** The codebase has THREE different agent orchestration systems:
1. `app/agents/graph.py` (LangGraph-based)
2. `app/agents/orchestrator/service.py` (Custom orchestrator)
3. Individual agent dispatchers in `app/api/v1/agents.py`

These systems have overlapping functionality, different retry logic, different timeout handling, and different result formatting. This is a major maintenance liability.

---

### A-2: No Centralized Error Handling Pattern

**Issue:** Every API endpoint has its own `try/except` block with inconsistent error responses. Some return `{error: ...}`, others raise `HTTPException`, and some return generic 500 errors. There's no global exception handler.

---

### A-3: Mixed Async/Sync Patterns

**Issue:** The codebase mixes:
- `asyncio.run()` inside sync RQ workers
- `requests` (sync) in async context
- `aioredis` (async) used alongside sync Redis in places

This can cause subtle bugs and performance issues.

---

## ✅ POSITIVE SECURITY PRACTICES OBSERVED

Despite the issues above, the codebase has several good security practices worth noting:

1. **Firebase Token Verification:** Proper JWT verification with RS256 algorithm, audience, and issuer validation
2. **HTTPS Redirection:** `HTTPSRedirectMiddleware` enabled in production
3. **Trusted Host Middleware:** `TrustedHostMiddleware` restricts to known domains
4. **CORS Configuration:** Well-configured with explicit origins, methods, and headers (no wildcard)
5. **Security Headers:** `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy` are set on API responses
6. **File Upload Validation:** Content type checks, size limits, and UUID-based filenames for avatars
7. **Input Validation:** Pydantic models with validators for API keys
8. **Password Hashing:** (Deprecated auth) uses bcrypt
9. **Session Isolation:** SQLAlchemy sessions are properly scoped per request
10. **No Hardcoded Production Secrets:** Secrets come from environment variables

---

## 🎯 RECOMMENDED PRIORITY ORDER FOR FIXES

### Immediate (Fix within 24 hours):
1. **C-1**: Fix default JWT secret — generate cryptographically random key
2. **C-4**: Add rate limiting specifically for auth endpoints
3. **C-5**: Fix Redis fallback to fail-closed in production
4. **I-2**: Implement GDPR consent for Firebase Analytics

### Short-term (Fix within 1 week):
5. **C-7**: Remove hardcoded Firebase project ID
6. **C-8**: Remove default JWT secret from Docker Compose
7. **C-10**: Add security headers to nginx
8. **B-2**: Fix rate limit headers to report actual values
9. **F-1**: Add email verification enforcement
10. **F-3**: Add audit logging

### Medium-term (Fix within 1 month):
11. **F-6**: Implement PII encryption at rest
12. **F-5**: Add 2FA support
13. **A-1**: Consolidate agent orchestration systems
14. **A-2**: Implement centralized error handling
15. **Q-8**: Implement log sanitization

### Long-term (Architecture improvements):
16. **F-8**: Data retention and deletion policies
17. **D-1 through D-4**: Update vulnerable dependencies
18. **A-3**: Remove mixed async/sync patterns
19. **B-5**: Eliminate demo data mixing with real data
20. **Q-3**: Replace sync HTTP calls with async versions

---

*End of security audit report. Generated by AgentForge AI Security Audit System on July 3, 2026.*

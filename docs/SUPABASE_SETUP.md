# Supabase PostgreSQL Integration & Setup Guide

This guide details the database architecture, connection pooler configuration, Alembic migrations, and Row Level Security (RLS) policies for running SAHAYAK AI with Supabase PostgreSQL in staging and production environments, while maintaining zero-credential local SQLite operation for development.

---

## 1. Architectural Strategy

SAHAYAK AI implements a resilient dual-tier database strategy:
- **Local Development**: Completely self-contained local SQLite (`sqlite+aiosqlite:///./sahayak.db`). Requires no external network access, cloud credentials, Docker containers, or pre-configured services.
- **Staging & Production**: Supabase PostgreSQL managed database accessed via SQLAlchemy 2.0 asynchronous engine (`asyncpg`) with Supavisor connection pooling.
- **Graceful Startup Resilience**: The application features automatic startup fallback logic. If `DATABASE_URL` is configured for an unreachable PostgreSQL instance during local development or startup (e.g. invalid credentials, offline host, or unconfigured network), SAHAYAK AI logs a warning with sanitized credentials and automatically switches to local SQLite so development and voice assistant testing are never blocked.
- **Dialect-Agnostic Schema**: Models and migrations use standard SQLAlchemy `JSON` types and boolean expressions (`sa.true()`), compiling seamlessly to native `JSON` and `true` on PostgreSQL, and `TEXT` JSON and `1` on SQLite.

---

## 2. Supabase Provisioning & Connection Topologies

### 2.1 Project Creation
1. Navigate to [Supabase Dashboard](https://supabase.com/dashboard) and create a new project (e.g., `sahayak-ai-prod`).
2. Select an AWS region close to Indian users (e.g., `ap-south-1` Mumbai) for minimal network and audio latency.
3. Choose a strong, high-entropy database password and securely record it.

### 2.2 Connection Topologies & Ports

Supabase provides three distinct connection topologies:

| Connection Mode | Port | Host Format | Username Format | Recommended Use Case in SAHAYAK AI |
|---|---|---|---|---|
| **Supavisor Transaction Pooler** | `6543` | `aws-0-[region].pooler.supabase.com` | `postgres.[project-ref]` | **Runtime Application Server**: High concurrency, stateless request pooling, full IPv4/IPv6 dual-stack support. |
| **Supavisor Session Pooler** | `5432` | `aws-0-[region].pooler.supabase.com` | `postgres.[project-ref]` | **Alembic Migrations & DDL**: Dedicated persistent connection per session, handles DDL and advisory locks, IPv4 supported. |
| **Direct Database Connection** | `5432` | `db.[project-ref].supabase.co` | `postgres` | **Direct Connection**: Requires IPv6 network connectivity or Supabase paid IPv4 add-on. Recommended only when IPv6 is available. |

### 2.3 Supavisor Pooler Driver Requirements (`asyncpg`)

When connecting via the Supavisor Transaction Pooler on port `6543`, connections are multiplexed at transaction boundaries. This introduces two critical driver requirements handled automatically by SAHAYAK AI:
1. **Disable Prepared Statement Caching**: Because the transaction pooler routes queries across different physical PostgreSQL backend connections, cached prepared statement names collide, triggering `DuplicatePreparedStatementError: prepared statement "_pg3_0" already exists`.
   - **Configuration**: SAHAYAK AI automatically injects `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` into the async engine when connecting to PostgreSQL.
   - **Warning**: Never pass `statement_cache_size=0` in the URL query string (`?statement_cache_size=0`), because `asyncpg` parses query parameters as strings and raises `TypeError: '<' not supported between instances of 'str' and 'int'`.
2. **SSL Parameter Normalization**: `asyncpg` requires `ssl=require`. The legacy libpq/psycopg parameter `sslmode=require` causes `TypeError: connect() got an unexpected keyword argument 'sslmode'`. SAHAYAK AI's URL normalizer automatically converts `sslmode=` to `ssl=`.

### 2.4 Password URL Encoding
If your database password contains special characters (such as `@`, `:`, `/`, `#`, `%`, `?`, or `!`), it **must** be URL-percent-encoded in `DATABASE_URL` according to RFC 3986. Otherwise, SQLAlchemy's `make_url` parser misinterprets the userinfo boundaries, corrupting the host or port.

You can encode your password using Python:
```python
import urllib.parse
password = "My@Password#2026!"
encoded = urllib.parse.quote_plus(password)
print(encoded)  # Output: My%40Password%232026%21
```

---

## 3. Environment Configuration Templates

### 3.1 Local Development Template (`.env`)
Configured for zero-credential, offline-first SQLite operation:
```bash
# Core Application
APP_NAME="SAHAYAK AI"
APP_VERSION="1.0.0"
APP_DEBUG=true
ENVIRONMENT="development"
LOG_LEVEL="INFO"

# Server
BACKEND_HOST="0.0.0.0"
BACKEND_PORT=8000
BACKEND_WORKERS=1
FRONTEND_URL="http://localhost:5173"

# Database (Local SQLite - Zero external setup needed)
DATABASE_URL="sqlite:///./sahayak.db"

# Security
SECRET_KEY="development-secret-key-change-in-production-min-32-chars"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_MINUTES=1440

# Google Gemini Live
GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere"
GEMINI_LIVE_MODEL="gemini-2.0-flash-exp"

# Google OAuth (Optional in local dev)
ENABLE_OAUTH=false
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""

# Feature Flags
ENABLE_ADMIN_PANEL=false
ENABLE_AUDIO_RECORDING=false
```

### 3.2 Production / Staging Template (`.env.production`)
Configured for Supabase PostgreSQL via the Supavisor Transaction Pooler (Port 6543):
```bash
# Core Application
APP_NAME="SAHAYAK AI"
APP_VERSION="1.0.0"
APP_DEBUG=false
ENVIRONMENT="production"
LOG_LEVEL="INFO"

# Server
BACKEND_HOST="0.0.0.0"
BACKEND_PORT=8000
BACKEND_WORKERS=4
FRONTEND_URL="https://sahayak.yourdomain.com"

# Database (Supabase PostgreSQL via Supavisor Transaction Pooler on Port 6543)
# Format: postgresql://postgres.[PROJECT_REF]:[ENCODED_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_URL="postgresql://postgres.abcdefghijklm:My%40Password%232026%21@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

# Direct / Session URL (For running Alembic DDL migrations via Session Pooler on Port 5432)
DIRECT_URL="postgresql://postgres.abcdefghijklm:My%40Password%232026%21@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

# Security
SECRET_KEY="production-high-entropy-64-character-cryptographic-secret-key"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_MINUTES=1440

# Google Gemini Live
GEMINI_API_KEY="AIzaSyProductionKeyHere..."
GEMINI_LIVE_MODEL="gemini-2.0-flash-exp"

# Google OAuth
ENABLE_OAUTH=true
GOOGLE_CLIENT_ID="1234567890-prod.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-ProductionSecretHere"

# Feature Flags
ENABLE_ADMIN_PANEL=true
ENABLE_AUDIO_RECORDING=false
```

---

## 4. Alembic Migration Workflow

### 4.1 Running Migrations Online
To execute migrations against your Supabase database, use the Session Pooler (port `5432`) to ensure full support for DDL transactions and table locks:

```bash
# Option A: Set DATABASE_URL in PowerShell
cd backend
$env:DATABASE_URL="postgresql://postgres.[REF]:[ENCODED_PASS]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require"
.\venv\Scripts\alembic.exe upgrade head

# Option B: Pass via Alembic CLI -x db_url argument
cd backend
.\venv\Scripts\alembic.exe -x db_url="postgresql://postgres.[REF]:[ENCODED_PASS]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require" upgrade head
```

### 4.2 Verifying Zero Schema Drift (`alembic check`)
Verify that the database schema precisely matches the SQLAlchemy model definitions without any pending migrations or drift:
```bash
cd backend
.\venv\Scripts\alembic.exe check
```
**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
No new upgrade operations detected.
```

### 4.3 Generating Offline SQL Migration Scripts
To review DDL before execution or apply changes directly inside the Supabase Dashboard SQL Editor:
```bash
cd backend
.\venv\Scripts\alembic.exe -x db_url="postgresql+asyncpg://postgres:dummy@localhost:5432/postgres" upgrade head --sql > supabase_migration.sql
```
This generates a complete transactional SQL script containing:
- Enum type definitions (`userrole`, `sessionstatus`, `speakertype`, `knowledgecategory`, `evaluationresult`)
- All 6 application tables with foreign keys and indexes
- Dialect-clean boolean defaults (`DEFAULT true`) and `JSON` column definitions
- Version stamping into `alembic_version`

---

## 5. Row Level Security (RLS) & Security Policies

Supabase exposes databases through auto-generated PostgREST HTTP APIs. To ensure that client requests with public anon keys cannot access or tamper with internal voice assistant data, execute the following security policies in the **Supabase Dashboard SQL Editor**:

```sql
-- =============================================================================
-- SAHAYAK AI: Row Level Security (RLS) Policies
-- =============================================================================

-- 1. Enable RLS on all 6 application tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_records ENABLE ROW LEVEL SECURITY;

-- 2. Knowledge Documents: Public verified knowledge base is readable by all
CREATE POLICY "Public read verified knowledge documents"
    ON knowledge_documents FOR SELECT
    USING (verified_at IS NOT NULL);

-- 3. Users: Authenticated users can view their own profile
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid()::text = id);

-- 4. Sessions: Users can view their own sessions; anonymous sessions visible to session holder
CREATE POLICY "Users can view own sessions"
    ON sessions FOR SELECT
    USING (auth.uid()::text = user_id OR user_id IS NULL);

-- 5. Conversation Messages: Accessible if parent session belongs to user
CREATE POLICY "Users can view messages for own sessions"
    ON conversation_messages FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = conversation_messages.session_id
              AND (sessions.user_id = auth.uid()::text OR sessions.user_id IS NULL)
        )
    );

-- 6. Feedback: Any user can submit feedback for an active session
CREATE POLICY "Allow feedback creation"
    ON feedback FOR INSERT
    WITH CHECK (true);

-- 7. Evaluation Records: Restricted to administrative access
CREATE POLICY "Admins can view evaluation records"
    ON evaluation_records FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()::text
              AND users.role = 'ADMIN'
        )
    );

-- Note: The SAHAYAK AI backend connects with the postgres superuser / service role,
-- which automatically bypasses Row Level Security for all operations.
```

---

## 6. Troubleshooting & Common Pitfalls

| Issue | Root Cause | Solution |
|---|---|---|
| `TypeError: '<' not supported between instances of 'str' and 'int'` | `statement_cache_size=0` was passed in the URL query string instead of engine connect args. | Pass `statement_cache_size: 0` in SQLAlchemy's `connect_args`, never in the URL string. |
| `TypeError: connect() got an unexpected keyword argument 'sslmode'` | `asyncpg` does not recognize `sslmode`. It requires `ssl=require`. | SAHAYAK AI's `get_async_database_url` automatically converts `sslmode=` to `ssl=`. |
| `DuplicatePreparedStatementError: prepared statement "_pg3_0" already exists` | Using Supavisor Transaction Pooler (port `6543`) with prepared statement caching enabled. | `create_engine_instance` sets `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` for PostgreSQL. |
| `DatatypeMismatch: column is of type boolean but default expression is of type integer` | Migration had `server_default=sa.text('1')` which PostgreSQL rejects. | Use `server_default=sa.true()`, which compiles to `DEFAULT true` on PostgreSQL and `DEFAULT (1)` on SQLite. |
| `Target database is not up to date` / detected dropped tables in `alembic check` | `migrations/env.py` imported `Base` without importing `app.models.models`. | `env.py` imports `app.models.models`, populating all 6 tables in `Base.metadata.tables`. |
| Direct connection timeout on port `5432` (`[WinError 1225]` or timeout) | `db.[REF].supabase.co` resolves to IPv6 addresses only on standard Supabase projects. | Connect via Supavisor pooler (`aws-0-[REGION].pooler.supabase.com`), which supports IPv4 and IPv6 dual-stack. |
| URL parsing error or corrupted hostname/port | Database password contains `@`, `:`, `#`, `%`, or `/` without URL encoding. | URL-encode the password with `urllib.parse.quote_plus(password)`. |
| Startup blocked when database host is offline | Missing credentials or bad network causing application crash. | Handled automatically: `init_db()` catches PostgreSQL exceptions, logs a warning, and falls back to local SQLite. |

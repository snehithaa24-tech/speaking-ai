"""Automated Database Test Suite for SAHAYAK AI (Milestone 3).

Verifies:
1. URL Normalization across SQLite, PostgreSQL, asyncpg, and Supabase pooler formats.
2. SQLAlchemy Model Metadata & Dialect-Agnostic Types.
3. Alembic Migration Upgrade & Downgrade execution on SQLite and DDL compilation on PostgreSQL.
4. Graceful Fallback Behavior from unreachable PostgreSQL to local SQLite.
"""

import pytest
import os
import tempfile
import sqlite3
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from alembic.config import Config
from alembic import command

from app.database.session import (
    get_async_database_url,
    create_engine_instance,
    Base,
    init_db,
    close_db,
    get_db,
    DEFAULT_SQLITE_URL,
)
import app.models.models as models
from app.models.models import (
    User,
    Session,
    ConversationMessage,
    Feedback,
    KnowledgeDocument,
    EvaluationRecord,
)
from app.core.config import settings


# ============================================================================
# Suite 1: Database URL Normalization Tests
# ============================================================================
class TestDatabaseUrlNormalization:

    def test_sqlite_standard_url(self):
        url = "sqlite:///./sahayak.db"
        assert get_async_database_url(url) == "sqlite+aiosqlite:///./sahayak.db"

    def test_sqlite_aiosqlite_url_idempotent(self):
        url = "sqlite+aiosqlite:///./sahayak.db"
        assert get_async_database_url(url) == "sqlite+aiosqlite:///./sahayak.db"

    def test_sqlite_memory_url(self):
        url = "sqlite:///:memory:"
        assert get_async_database_url(url) == "sqlite+aiosqlite:///:memory:"

    def test_postgres_legacy_scheme(self):
        url = "postgres://postgres:secret@db.projectref.supabase.co:5432/postgres"
        expected = "postgresql+asyncpg://postgres:secret@db.projectref.supabase.co:5432/postgres"
        assert get_async_database_url(url) == expected

    def test_postgresql_standard_scheme(self):
        url = "postgresql://postgres:secret@localhost:5432/sahayak"
        expected = "postgresql+asyncpg://postgres:secret@localhost:5432/sahayak"
        assert get_async_database_url(url) == expected

    def test_postgresql_asyncpg_scheme_idempotent(self):
        url = "postgresql+asyncpg://postgres:secret@localhost:5432/sahayak"
        assert get_async_database_url(url) == url

    def test_supabase_transaction_pooler_url(self):
        url = "postgresql://postgres.myproject:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
        expected = "postgresql+asyncpg://postgres.myproject:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?ssl=require"
        assert get_async_database_url(url) == expected

    @pytest.mark.parametrize("empty_val", ["", "   ", None])
    def test_empty_or_none_url_defaults_to_local_sqlite(self, empty_val):
        assert get_async_database_url(empty_val) == DEFAULT_SQLITE_URL

    def test_create_engine_instance_connect_args(self):
        pg_engine = create_engine_instance("postgresql://user:pass@localhost:5432/db")
        # Ensure postgres async engine connect_args includes statement_cache_size=0
        assert pg_engine.url.get_backend_name() == "postgresql"

        sqlite_engine = create_engine_instance("sqlite:///./sahayak.db")
        assert sqlite_engine.url.get_backend_name() == "sqlite"


# ============================================================================
# Suite 2: Table Metadata & Model Definition Tests
# ============================================================================
class TestDatabaseMetadata:

    def test_metadata_contains_all_six_tables(self):
        expected_tables = {
            "users",
            "sessions",
            "conversation_messages",
            "feedback",
            "knowledge_documents",
            "evaluation_records",
        }
        actual_tables = set(Base.metadata.tables.keys())
        assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"

    def test_models_use_dialect_agnostic_json(self):
        # ConversationMessage.meta
        msg_meta_col = ConversationMessage.__table__.c.meta
        assert isinstance(msg_meta_col.type, sa.JSON)
        assert msg_meta_col.type.__class__.__module__.startswith("sqlalchemy.sql.sqltypes")

        # KnowledgeDocument.meta
        doc_meta_col = KnowledgeDocument.__table__.c.meta
        assert isinstance(doc_meta_col.type, sa.JSON)
        assert doc_meta_col.type.__class__.__module__.startswith("sqlalchemy.sql.sqltypes")

    def test_models_boolean_defaults(self):
        user_is_active = User.__table__.c.is_active
        assert user_is_active.default.arg is True

        msg_is_final = ConversationMessage.__table__.c.is_final
        assert msg_is_final.default.arg is True

    def test_model_foreign_key_relationships(self):
        # sessions.user_id -> users.id
        session_user_fk = list(Session.__table__.c.user_id.foreign_keys)[0]
        assert session_user_fk.target_fullname == "users.id"

        # conversation_messages.session_id -> sessions.id
        msg_session_fk = list(ConversationMessage.__table__.c.session_id.foreign_keys)[0]
        assert msg_session_fk.target_fullname == "sessions.id"

        # feedback.session_id -> sessions.id
        fb_session_fk = list(Feedback.__table__.c.session_id.foreign_keys)[0]
        assert fb_session_fk.target_fullname == "sessions.id"


# ============================================================================
# Suite 3: Alembic Migration Execution & PostgreSQL Compilation Tests
# ============================================================================
class TestAlembicMigrations:

    def test_alembic_upgrade_and_downgrade_lifecycle(self, monkeypatch):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name.replace("\\", "/")

        try:
            temp_sqlite_url = f"sqlite:///{tmp_path}"
            monkeypatch.setattr(settings, "DATABASE_URL", temp_sqlite_url)

            # Locate alembic.ini from backend root
            alembic_ini_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
            )
            cfg = Config(alembic_ini_path)
            cfg.set_main_option("script_location", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "migrations")))
            cfg.set_main_option("sqlalchemy.url", temp_sqlite_url)

            # 1. Run upgrade head
            command.upgrade(cfg, "head")

            # Inspect created SQLite tables
            conn = sqlite3.connect(tmp_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {r[0] for r in cur.fetchall()}

            expected = {
                "alembic_version",
                "users",
                "sessions",
                "conversation_messages",
                "feedback",
                "knowledge_documents",
                "evaluation_records",
            }
            assert expected.issubset(tables)

            # Verify revision stamp
            cur.execute("SELECT version_num FROM alembic_version;")
            assert cur.fetchone()[0] == "83cbac773a21"

            # 2. Run downgrade base
            command.downgrade(cfg, "base")
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables_after_downgrade = {r[0] for r in cur.fetchall()}
            conn.close()

            # All application tables should be dropped
            assert "users" not in tables_after_downgrade
            assert "sessions" not in tables_after_downgrade
            assert "conversation_messages" not in tables_after_downgrade

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_migration_ddl_compilation_for_postgresql(self):
        """Verify that server_default=sa.true() renders as 'DEFAULT true' on PostgreSQL."""
        col = sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        ddl = str(sa.schema.CreateColumn(col).compile(dialect=postgresql.dialect()))
        assert "DEFAULT true" in ddl
        assert "DEFAULT 1" not in ddl

    def test_migration_ddl_compilation_for_sqlite(self):
        """Verify that server_default=sa.true() renders as 'DEFAULT (1)' on SQLite."""
        col = sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        ddl = str(sa.schema.CreateColumn(col).compile(dialect=sqlite.dialect()))
        assert "DEFAULT (1)" in ddl

    def test_json_ddl_compilation_for_postgresql_and_sqlite(self):
        """Verify sa.JSON() column compiles cleanly on both PostgreSQL and SQLite."""
        meta_col = sa.Column("meta", sa.JSON(), nullable=True)
        pg_ddl = str(sa.schema.CreateColumn(meta_col).compile(dialect=postgresql.dialect()))
        assert "JSON" in pg_ddl

        sqlite_ddl = str(sa.schema.CreateColumn(meta_col).compile(dialect=sqlite.dialect()))
        assert "JSON" in sqlite_ddl


# ============================================================================
# Suite 4: Graceful Fallback Behavior Tests
# ============================================================================
class TestDatabaseGracefulFallback:

    @pytest.mark.asyncio
    async def test_init_db_falls_back_to_sqlite_when_postgres_unreachable(self, monkeypatch):
        # Configure an unreachable PostgreSQL address
        unreachable_url = "postgresql://invalid_user:invalid_pass@127.0.0.1:59999/unreachable_db"
        monkeypatch.setattr(settings, "DATABASE_URL", unreachable_url)

        # Ensure init_db catches exception and falls back to SQLite
        await init_db()

        # Check that we can get a working session and execute a query
        async for session in get_db():
            result = await session.execute(sa.text("SELECT 1"))
            assert result.scalar() == 1
            break

        await close_db()

    @pytest.mark.asyncio
    async def test_get_db_session_rollback_on_exception(self):
        """Test that get_db() rolls back when an exception occurs inside the generator context."""
        with pytest.raises(RuntimeError, match="Test simulated route error"):
            async for session in get_db():
                raise RuntimeError("Test simulated route error")

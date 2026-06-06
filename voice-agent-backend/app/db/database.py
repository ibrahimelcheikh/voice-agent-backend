from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def reset_schema():
    """Full wipe + recreate, robust to orphan tables.

    `Base.metadata.drop_all` only drops tables it knows about, in FK order — but this
    DB still carries tables from the OLD restaurant schema (reservations/orders/faqs)
    whose foreign keys reference `agents`. Those orphans aren't in Base.metadata, so a
    model-only drop_all fails with DependentObjectsStillExistError. Dropping and
    recreating the `public` schema clears everything (orphans included) reliably."""
    import app.models.models  # noqa: F401 — register all models on Base before create_all
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)


async def ensure_columns():
    """Additive, idempotent schema patch for columns introduced after the initial
    deploy. `Base.metadata.create_all(checkfirst=True)` only creates MISSING TABLES —
    it never adds new COLUMNS to a table that already exists. On a persistent DB (e.g.
    Railway, where we deliberately keep data and no longer wipe/reseed), new model
    columns would therefore be silently absent and every query referencing them would
    fail. `ADD COLUMN IF NOT EXISTS` is safe to run on every boot: it adds the column
    on the first deploy that needs it and no-ops thereafter. Never destroys data."""
    statements = [
        # Drop dead ORPHAN tables left by the very first (restaurant-era) schema. They
        # reference `agents` and are not in Base.metadata, so they (a) block a model-only
        # drop_all and (b) — critically — share the names the niche feature might otherwise
        # have reused. The new restaurant tables deliberately use distinct names
        # (restaurant_reservations / restaurant_orders / menu_items), so dropping these
        # legacy names is always safe and never touches live niche data.
        "DROP TABLE IF EXISTS faqs CASCADE",
        "DROP TABLE IF EXISTS orders CASCADE",
        "DROP TABLE IF EXISTS reservations CASCADE",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMP",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_outcome VARCHAR",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS appointment_id VARCHAR",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS purpose VARCHAR",
        # Multi-tenant foundation: tenant_id on every domain table + staff role/tenant.
        # `tenants` itself is a new table, so create_all adds it; these only patch the
        # tenant_id column onto pre-existing tables on a persistent (Railway) DB.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR",
        "ALTER TABLE behavior_configs ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE whatsapp_conversations ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE clinics ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
        "ALTER TABLE insurance_providers ADD COLUMN IF NOT EXISTS tenant_id VARCHAR",
    ]
    async with engine.begin() as conn:
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:  # pragma: no cover - defensive; never block startup
                print(f"[migrate] skipped {stmt!r}: {type(e).__name__}: {e}")


# Domain tables that gain a tenant_id and must be backfilled to the default tenant on
# an existing (already-seeded) database so the original clinic keeps working unchanged.
_TENANT_SCOPED_TABLES = (
    "users", "behavior_configs", "agents", "campaigns", "calls",
    "whatsapp_conversations", "clinics", "doctors", "services", "patients",
    "appointments", "insurance_providers",
)

# Fixed ids/values for the migrated original clinic — see seed.py (kept in sync).
DEFAULT_TENANT_ID = "tenant-001"
_DEFAULT_TENANT_NAME = "Prime Health Clinic"
_DEFAULT_TENANT_NUMBER = "+16575347796"
_DEFAULT_TENANT_GREETING = (
    "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?"
)


async def backfill_default_tenant():
    """Migrate an EXISTING single-clinic database to the multi-tenant model in place.

    On a persistent DB (Railway) the original clinic's rows have NULL tenant_id after the
    tenant_id columns are added. This idempotently (a) creates the original clinic as
    `tenant-001` if it doesn't exist, then (b) assigns every still-unscoped domain row to
    it. Fresh DBs are handled by the seed instead; this is a no-op there (the seed already
    sets tenant_id on every row). Never destroys data — only fills NULLs."""
    async with engine.begin() as conn:
        # Skip cleanly if the tenants table isn't there yet (shouldn't happen — create_all
        # runs first — but never block startup).
        try:
            exists = (await conn.execute(text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants'"
            ))).first()
        except Exception as e:
            print(f"[migrate] tenant backfill skipped (no tenants table): {e}")
            return
        if not exists:
            return

        # Is there anything to migrate? Only act when a domain row has a NULL tenant_id.
        try:
            orphan = (await conn.execute(text(
                "SELECT 1 FROM clinics WHERE tenant_id IS NULL LIMIT 1"
            ))).first()
            orphan = orphan or (await conn.execute(text(
                "SELECT 1 FROM appointments WHERE tenant_id IS NULL LIMIT 1"
            ))).first()
        except Exception:
            orphan = None
        if not orphan:
            return

        # Ensure the default tenant exists (reuse the original clinic's number so inbound
        # calls to it route here). Derive its number from the existing clinic row if present.
        clinic_number = None
        try:
            row = (await conn.execute(text(
                "SELECT phone FROM clinics ORDER BY created_at LIMIT 1"
            ))).first()
            clinic_number = row[0] if row else None
        except Exception:
            clinic_number = None
        number = clinic_number or _DEFAULT_TENANT_NUMBER

        await conn.execute(
            text("""
                INSERT INTO tenants
                    (id, business_name, niche, twilio_phone_number, default_language,
                     supported_languages, timezone, greeting_message, knowledge_base,
                     config, is_active)
                VALUES
                    (:id, :name, 'clinic', :num, 'en',
                     '["en"]'::json, 'Asia/Beirut', :greeting, '{}'::json, '{}'::json, true)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": DEFAULT_TENANT_ID, "name": _DEFAULT_TENANT_NAME, "num": number,
             "greeting": _DEFAULT_TENANT_GREETING},
        )

        for table in _TENANT_SCOPED_TABLES:
            try:
                await conn.execute(text(
                    f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL"
                ), {"tid": DEFAULT_TENANT_ID})
            except Exception as e:
                print(f"[migrate] backfill {table} skipped: {type(e).__name__}: {e}")
        print(f"[migrate] backfilled existing data to default tenant {DEFAULT_TENANT_ID}")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

"""
Enforced multi-tenant query scoping.

Tenant isolation in the niche/data functions used to work by *convention*: every
query manually added `.where(Model.tenant_id == tenant_id)`. That is easy to forget
silently — omit the filter (or pass `tenant_id=None`) and the query quietly returns
EVERY tenant's rows instead of failing. This module converts that convention into an
enforced, structural guarantee: a tenant-scoped read with no tenant_id fails loud
instead of leaking.

It is a thin wrapper around SQLAlchemy `select(...).where(...)` — NOT an ORM rewrite.

Helpers:
  * require_tenant_id(tenant_id, context)  — assert a non-empty tenant_id is present;
                                             raise a clear ValueError otherwise.
  * scope_query(query, model, tenant_id)   — add `model.tenant_id == tenant_id` to an
                                             EXISTING query (drop-in for the old
                                             per-module `_scope` helper). Enforced:
                                             raises when tenant_id is missing.
  * scoped_query(model, tenant_id)         — build a FRESH `select(model)` already
                                             filtered by tenant. Enforced the same way.

Because every tenant-scoped read in the data functions flows through these helpers,
the tenant filter can no longer be silently omitted.
"""
from sqlalchemy import select


def require_tenant_id(tenant_id, context: str = "query"):
    """Guarantee a tenant_id is present before any tenant-scoped query runs.

    Raises ValueError (fail loud) when tenant_id is None/empty, naming the calling
    context so the omission is immediately visible instead of silently returning
    another tenant's data. Returns the tenant_id unchanged when valid."""
    if not tenant_id:
        raise ValueError(
            f"tenant_id is required for {context} — refusing to run an unscoped, "
            "cross-tenant query"
        )
    return tenant_id


def scope_query(query, model, tenant_id, *, context: str | None = None):
    """Add the tenant filter to an existing query. Drop-in replacement for the old
    module-level `_scope`, except it now ENFORCES the tenant_id instead of skipping
    the filter when it is missing."""
    require_tenant_id(tenant_id, context or getattr(model, "__name__", "query"))
    return query.where(model.tenant_id == tenant_id)


def scoped_query(model, tenant_id, *, context: str | None = None):
    """Build a fresh `select(model)` already scoped to the tenant. Enforces the
    tenant_id the same way `scope_query` does."""
    require_tenant_id(tenant_id, context or getattr(model, "__name__", "query"))
    return select(model).where(model.tenant_id == tenant_id)

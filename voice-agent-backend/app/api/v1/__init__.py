"""Versioned REST API (/api/v1) serving the AtlasPrimeX merchant app and PrimeOps
console. Reuses the existing multi-tenant models; operators (User.tenant_id IS NULL)
see all tenants, merchants are scoped to their own tenant."""
from fastapi import APIRouter

from . import auth, tenants, services, calls, appointments, settings as settings_routes
from . import alerts, tickets, users, analytics, leads

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["v1 · Auth"])
router.include_router(tenants.router, prefix="/tenants", tags=["v1 · Tenants & Branches"])
router.include_router(services.router, prefix="/services", tags=["v1 · Services"])
router.include_router(calls.router, prefix="/calls", tags=["v1 · Calls & Transcripts"])
router.include_router(appointments.router, prefix="/appointments", tags=["v1 · Appointments"])
router.include_router(settings_routes.router, prefix="/settings", tags=["v1 · Settings"])
router.include_router(alerts.router, prefix="/alerts", tags=["v1 · Alerts"])
router.include_router(tickets.router, prefix="/tickets", tags=["v1 · Tickets"])
router.include_router(users.router, prefix="/users", tags=["v1 · Users"])
router.include_router(analytics.router, prefix="/analytics", tags=["v1 · Analytics"])
router.include_router(leads.router, prefix="/leads", tags=["v1 · Leads"])

"""
Appointment reminder calls API.

  POST /reminders/call   — manually place a reminder call for one appointment
  GET  /reminders/due    — preview which appointments are due for a reminder
  POST /reminders/sweep  — run the due-sweep on demand (same job the scheduler runs)

The automatic 15-minute sweep is wired in app/main.py (APScheduler); these endpoints
are the manual surface and a way to inspect/trigger it.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.services.reminder_service import (
    place_reminder_call, find_due_appointments, run_reminder_sweep, human_date, human_time,
)

router = APIRouter()


class ReminderCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appointment_id: str


@router.post("/call")
async def trigger_reminder_call(body: ReminderCallRequest):
    """Place an outbound reminder call for a specific appointment right now."""
    result = await place_reminder_call(body.appointment_id)
    if not result.get("success"):
        reason = result.get("reason", "unknown")
        status = 404 if reason == "appointment_not_found" else 422
        raise HTTPException(status_code=status, detail=result)
    return result


@router.get("/due")
async def list_due_reminders():
    """Appointments occurring within the reminder window that haven't been called yet."""
    due = await find_due_appointments()
    return {
        "count": len(due),
        "items": [
            {"appointment_id": a.id, "date": a.date, "time": a.time,
             "when": f"{human_date(a.date)} at {human_time(a.time)}",
             "status": a.status.value}
            for a in due
        ],
    }


@router.post("/sweep")
async def run_sweep_now():
    """Run the reminder sweep immediately (places calls for all due appointments)."""
    return await run_reminder_sweep()

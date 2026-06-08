"""
Enable custom SIP X-headers on the EXISTING LiveKit inbound trunk (one-time, idempotent).

    python scripts/enable_sip_x_headers.py

Phase 3a threads the caller's IVR-chosen language to the agent via a custom SIP header
`X-Language` (set by the Twilio webhook on the <Dial><Sip> URI). LiveKit only surfaces
custom headers as participant attributes when the inbound trunk has `include_headers` set.
This script flips that on for the existing trunk(s) WITHOUT recreating them, mapping
`X-Language` -> the `sip.language` participant attribute the agent reads.

It is safe and reversible:
  * It only ADDS header forwarding — it never changes routing, numbers, or auth.
  * A direct-SIP call with no `X-Language` header simply has no attribute, and the agent
    defaults to English. So running this never changes how English calls behave.

Idempotent: re-running is a no-op once the trunk already forwards X-headers.

Requires LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET in the environment (.env).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from livekit import api  # noqa: E402
from app.core.config import settings  # noqa: E402

_HEADER_MAP = {"X-Language": "sip.language"}


def _already_enabled(trunk) -> bool:
    has_x = getattr(trunk, "include_headers", 0) in (
        api.SIPHeaderOptions.SIP_X_HEADERS, api.SIPHeaderOptions.SIP_ALL_HEADERS)
    mapping = dict(getattr(trunk, "headers_to_attributes", {}) or {})
    return has_x and mapping.get("X-Language") == "sip.language"


def _replacement_info(t) -> api.SIPInboundTrunkInfo:
    """A full SIPInboundTrunkInfo copied from the existing trunk, with X-header forwarding
    turned on. `replace` requires the WHOLE info, so we preserve every routing/auth field."""
    return api.SIPInboundTrunkInfo(
        sip_trunk_id=t.sip_trunk_id,
        name=t.name,
        metadata=getattr(t, "metadata", "") or "",
        numbers=list(getattr(t, "numbers", []) or []),
        allowed_addresses=list(getattr(t, "allowed_addresses", []) or []),
        allowed_numbers=list(getattr(t, "allowed_numbers", []) or []),
        auth_username=getattr(t, "auth_username", "") or "",
        auth_password=getattr(t, "auth_password", "") or "",
        krisp_enabled=getattr(t, "krisp_enabled", False),
        media_encryption=getattr(t, "media_encryption", 0),
        ringing_timeout=getattr(t, "ringing_timeout", None),
        max_call_duration=getattr(t, "max_call_duration", None),
        include_headers=api.SIPHeaderOptions.SIP_X_HEADERS,
        headers_to_attributes={**(dict(getattr(t, "headers_to_attributes", {}) or {})),
                               **_HEADER_MAP},
    )


async def main():
    lk = api.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        trunks = (await lk.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())).items
        if not trunks:
            print("⚠️  No inbound SIP trunks found — run scripts/setup_livekit_sip.py first.")
            return
        for t in trunks:
            if _already_enabled(t):
                print(f"✅ trunk {t.sip_trunk_id} ({t.name!r}) already forwards X-headers "
                      "(X-Language -> sip.language) — no change.")
                continue
            await lk.sip.update_sip_inbound_trunk(
                api.UpdateSIPInboundTrunkRequest(
                    sip_trunk_id=t.sip_trunk_id,
                    replace=_replacement_info(t),
                )
            )
            print(f"🔧 trunk {t.sip_trunk_id} ({t.name!r}) updated: include_headers=SIP_X_HEADERS, "
                  "X-Language -> sip.language. Direct-SIP calls are unaffected (default en).")
        print("\nDone.")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(main())

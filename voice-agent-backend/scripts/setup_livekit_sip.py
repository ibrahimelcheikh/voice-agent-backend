"""
One-time (idempotent) LiveKit SIP setup for Twilio — MULTI-TENANT.

    python scripts/setup_livekit_sip.py

Creates an inbound SIP trunk that accepts calls dialed to ANY of our tenants' numbers and
a dispatch rule that drops each incoming call into its own `call-<random>` room. The agent
worker (automatic dispatch) then joins that room and resolves WHICH tenant from the dialed
number on the SIP join.

WHY numbers=[] (accept any number):
    The inbound trunk's `numbers` field gates which DIALED numbers LiveKit will accept. If
    it is set to a single number, calls dialed to any OTHER number are REJECTED before a
    room is ever created — so the agent worker is never offered a job and the call just
    rings (this is exactly what broke multi-tenant inbound: each tenant has its own Twilio
    number, but the trunk only accepted the original one). Leaving `numbers` EMPTY makes the
    one trunk accept every tenant's number; the tenant is then resolved per-call from the
    dialed number. Security is still enforced by `allowed_addresses` (Twilio's IPs only).

This script is idempotent: it deletes any existing inbound trunks + dispatch rules first,
then recreates a clean trunk (numbers=[]) and rule, so re-running it never leaves a stale,
number-restricted trunk that would silently drop inbound calls.

Requires LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET in the environment (.env).
Run from the project root.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from livekit import api  # noqa: E402
from app.core.config import settings  # noqa: E402

# Twilio's SIP signaling IP ranges (so only Twilio can use the trunk).
# Full current list: https://www.twilio.com/docs/sip-trunking/ip-addresses
TWILIO_SIP_CIDRS = [
    "54.172.60.0/23", "54.244.51.0/24", "54.171.127.192/30",
    "35.156.191.128/25", "54.65.63.192/26", "54.169.127.128/26",
    "54.252.254.64/26", "177.71.206.192/26",
]


def livekit_sip_host() -> str:
    """Derive the project SIP host from LIVEKIT_URL.
    wss://<proj>.livekit.cloud -> <proj>.sip.livekit.cloud
    """
    host = settings.LIVEKIT_URL.replace("wss://", "").replace("ws://", "").rstrip("/")
    return host.replace(".livekit.cloud", ".sip.livekit.cloud")


async def _clear_existing(lk):
    """Delete existing inbound trunks + dispatch rules so re-running yields a clean,
    correct config (never a leftover number-restricted trunk that drops inbound calls).
    Best-effort: a deletion failure is logged but doesn't abort the (re)create below."""
    try:
        rules = (await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())).items
        for r in rules:
            try:
                await lk.sip.delete_sip_dispatch_rule(
                    api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=r.sip_dispatch_rule_id))
                print(f"🧹 deleted old dispatch rule {r.sip_dispatch_rule_id}")
            except Exception as e:
                print(f"⚠️ could not delete dispatch rule {r.sip_dispatch_rule_id}: {e}")
    except Exception as e:
        print(f"⚠️ could not list dispatch rules: {e}")

    try:
        trunks = (await lk.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())).items
        for t in trunks:
            try:
                await lk.sip.delete_sip_trunk(
                    api.DeleteSIPTrunkRequest(sip_trunk_id=t.sip_trunk_id))
                print(f"🧹 deleted old inbound trunk {t.sip_trunk_id} (numbers={list(t.numbers)})")
            except Exception as e:
                print(f"⚠️ could not delete inbound trunk {t.sip_trunk_id}: {e}")
    except Exception as e:
        print(f"⚠️ could not list inbound trunks: {e}")


async def setup_sip():
    lk = api.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        # 0) Clean slate — remove any prior (possibly number-restricted) trunk + rule.
        await _clear_existing(lk)

        # 1) Inbound SIP trunk — accepts calls to ANY tenant number from Twilio's IPs.
        #    numbers=[] => match any dialed number (multi-tenant). The agent resolves the
        #    tenant from the dialed number at call time.
        trunk = await lk.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name="Twilio Inbound (multi-tenant)",
                    numbers=[],                      # accept ANY dialed number
                    allowed_addresses=TWILIO_SIP_CIDRS,
                    krisp_enabled=True,              # server-side noise cancellation
                )
            )
        )
        print(f"✅ SIP inbound trunk created (accepts any number): {trunk.sip_trunk_id}")

        # 2) Dispatch rule — individual room per caller (room_prefix lives on Individual).
        rule = await lk.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix="call-",
                    )
                ),
                trunk_ids=[trunk.sip_trunk_id],
                name="Route all calls",
            )
        )
        print(f"✅ Dispatch rule created: {rule.sip_dispatch_rule_id}")

        sip_host = livekit_sip_host()
        number = settings.TWILIO_PHONE_NUMBER
        print("\n" + "=" * 64)
        print("DONE. Inbound trunk now accepts ALL tenant numbers (multi-tenant).")
        print("=" * 64)
        print(f"\nLiveKit project SIP host (verify in Dashboard → Settings → SIP):")
        print(f"    {sip_host}")
        print(f"\nOption A — TwiML <Dial><Sip> (Programmable Voice, current setup):")
        print(f"    app dials: sip:<dialed_tenant_number>@{sip_host};transport=tcp")
        print(f"    (the trunk accepts any number; the agent resolves the tenant from it)")
        print(f"\nOption B — Twilio Elastic SIP Trunk origination URI:")
        print(f"    sip:{sip_host};transport=tcp")
        print(f"\nTwilio voice webhook (each tenant number → POST):")
        print(f"    {settings.PUBLIC_URL}/twilio/inbound")
        print(f"\nReference Twilio number: {number}")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(setup_sip())

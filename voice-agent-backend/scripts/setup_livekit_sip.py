"""
One-time LiveKit SIP setup for Twilio.

    python scripts/setup_livekit_sip.py

Creates an inbound SIP trunk (matching the Twilio number) and a dispatch rule
that drops each incoming call into its own `call-<random>` room. The Pipecat /
LiveKit agent then joins that room (triggered by the LiveKit `participant_joined`
webhook — see app/api/routes/livekit_webhooks.py).

Requires LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET / TWILIO_PHONE_NUMBER
in the environment (.env). Run from the project root.
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


async def setup_sip():
    lk = api.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        # 1) Inbound SIP trunk — accepts calls to our Twilio number from Twilio's IPs.
        #    include_headers=SIP_X_HEADERS + headers_to_attributes maps the IVR's custom
        #    `X-Language` SIP header to a participant attribute (`sip.language`) the agent
        #    reads (Phase 3a). Harmless when absent (direct-SIP call) — the agent defaults
        #    to English. To enable this on an EXISTING trunk, run
        #    scripts/enable_sip_x_headers.py (no need to recreate the trunk).
        trunk = await lk.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name="Twilio Inbound",
                    numbers=[settings.TWILIO_PHONE_NUMBER],
                    allowed_addresses=TWILIO_SIP_CIDRS,
                    krisp_enabled=True,  # server-side noise cancellation
                    include_headers=api.SIPHeaderOptions.SIP_X_HEADERS,
                    headers_to_attributes={"X-Language": "sip.language"},
                )
            )
        )
        print(f"✅ SIP inbound trunk created: {trunk.sip_trunk_id}")

        # 2) Dispatch rule — individual room per caller (room_prefix lives on Individual),
        #    EXPLICITLY dispatching each inbound `call-*` room to our named agent. The agent
        #    worker registers with this same name (settings.AGENT_NAME, default
        #    "clinic-agent"); if the rule names an agent the worker doesn't, no job is
        #    dispatched and the call rings unanswered. room_config.agents is what makes the
        #    inbound SIP room request our agent by name.
        rule_kwargs = dict(
            rule=api.SIPDispatchRule(
                dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                    room_prefix="call-",
                )
            ),
            trunk_ids=[trunk.sip_trunk_id],
            name="Route all calls",
        )
        if settings.AGENT_NAME:
            rule_kwargs["room_config"] = api.RoomConfiguration(
                agents=[api.RoomAgentDispatch(agent_name=settings.AGENT_NAME)]
            )
        rule = await lk.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(**rule_kwargs)
        )
        print(f"✅ Dispatch rule created (dispatches to agent {settings.AGENT_NAME!r}): "
              f"{rule.sip_dispatch_rule_id}")

        sip_host = livekit_sip_host()
        number = settings.TWILIO_PHONE_NUMBER
        print("\n" + "=" * 64)
        print("DONE. Point Twilio at LiveKit SIP.")
        print("=" * 64)
        print(f"\nLiveKit project SIP host (verify in Dashboard → Settings → SIP):")
        print(f"    {sip_host}")
        print(f"\nOption A — TwiML <Dial><Sip> (Programmable Voice, current setup):")
        print(f"    app already returns: sip:{number}@{sip_host};transport=tcp")
        print(f"\nOption B — Twilio Elastic SIP Trunk origination URI:")
        print(f"    sip:{sip_host};transport=tcp")
        print(f"\nThen set the LiveKit webhook (Dashboard → Settings → Webhooks):")
        print(f"    {settings.PUBLIC_URL}/livekit/webhook")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(setup_sip())

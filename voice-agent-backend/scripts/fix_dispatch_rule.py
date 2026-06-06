"""
Fix the LiveKit SIP DISPATCH RULE so inbound `call-*` rooms are dispatched to our agent.

    python scripts/fix_dispatch_rule.py

Run this ONLY after inspecting with scripts/inspect_livekit_sip.py and confirming the
current rule doesn't dispatch to our worker's agent_name. It:

  1. DELETES every existing SIP dispatch rule (so there are no duplicates / stale rules
     that route calls to the wrong agent or to no agent).
  2. CREATES ONE clean dispatch rule: individual room per caller (prefix `call-`) that
     EXPLICITLY dispatches each room to agent_name = settings.AGENT_NAME ("clinic-agent"),
     via RoomConfiguration(agents=[RoomAgentDispatch(agent_name=...)]).

It does NOT touch the inbound SIP trunk(s) — numbers, allowed addresses, and the trunk
itself are left exactly as they are. The new rule is bound to all existing inbound trunks
(by their ids) so it applies to the same trunk the calls already arrive on.

Requires LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET in the environment (.env).
This script makes CHANGES — it is never run automatically; you run it by hand.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from livekit import api  # noqa: E402
from app.core.config import settings  # noqa: E402

AGENT_NAME = settings.AGENT_NAME or "clinic-agent"
ROOM_PREFIX = "call-"


async def main():
    print("=" * 64)
    print("Fix LiveKit SIP dispatch rule (trunk left untouched)")
    print(f"  Target agent_name : {AGENT_NAME!r}")
    print(f"  Room prefix       : {ROOM_PREFIX!r}")
    print("=" * 64)

    lk = api.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        # Show (but do not modify) the existing trunks the new rule will bind to.
        trunks = (await lk.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())).items
        trunk_ids = [t.sip_trunk_id for t in trunks]
        print(f"\nInbound trunks (untouched): {trunk_ids or '(none found)'}")

        # 1) Delete every existing dispatch rule.
        rules = (await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())).items
        print(f"\nDeleting {len(rules)} existing dispatch rule(s)...")
        for r in rules:
            await lk.sip.delete_sip_dispatch_rule(
                api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=r.sip_dispatch_rule_id))
            print(f"  🧹 deleted {r.sip_dispatch_rule_id} ({r.name!r})")

        # 2) Create ONE clean rule that explicitly dispatches call-* rooms to our agent.
        #    Bind to the existing trunk ids when present; an empty list applies to all trunks.
        rule = await lk.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix=ROOM_PREFIX,
                    )
                ),
                trunk_ids=trunk_ids,
                name="Route all calls -> clinic-agent",
                room_config=api.RoomConfiguration(
                    agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME)]
                ),
            )
        )
        print(f"\n✅ Created dispatch rule {rule.sip_dispatch_rule_id} "
              f"→ dispatches {ROOM_PREFIX}* rooms to agent {AGENT_NAME!r}")
        print("\nDone. Re-run scripts/inspect_livekit_sip.py to confirm the MATCH, then "
              "place a test call — the worker should log a JOB REQUEST.")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(main())

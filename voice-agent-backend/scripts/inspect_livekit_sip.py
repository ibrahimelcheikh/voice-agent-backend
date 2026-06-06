"""
READ-ONLY inspector for the LiveKit SIP setup.

    python scripts/inspect_livekit_sip.py [number]

Connects to LiveKit Cloud with the existing API credentials and PRINTS the current state —
it makes NO changes. Use it to see exactly how an inbound call is routed and, crucially,
which agent_name (if any) each dispatch rule targets, so you can compare it to the worker's
registered name (settings.AGENT_NAME, default "clinic-agent").

Prints:
  * every inbound SIP trunk (id, name, numbers it accepts, allowed addresses/numbers)
  * every dispatch rule (id, type, room prefix, and its room_config.agents -> the
    RoomAgentDispatch agent_name(s) it dispatches to, or "NO agent dispatch configured")
  * a routing analysis for a specific dialed number (default: TWILIO_PHONE_NUMBER):
    which trunk(s) accept it and which rule(s) apply, and what agent each dispatches to.

Requires LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET in the environment (.env).
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


def _rule_kind_and_prefix(rule_info):
    """Return (kind, room_prefix_or_name) for a SIPDispatchRuleInfo's oneof rule."""
    r = getattr(rule_info, "rule", None)
    if r is None:
        return "unknown", ""
    if r.HasField("dispatch_rule_individual"):
        ind = r.dispatch_rule_individual
        return "individual", getattr(ind, "room_prefix", "") or "(no prefix)"
    if r.HasField("dispatch_rule_direct"):
        d = r.dispatch_rule_direct
        return "direct", getattr(d, "room_name", "") or "(no room name)"
    if r.HasField("dispatch_rule_callee"):
        c = r.dispatch_rule_callee
        return "callee", getattr(c, "room_prefix", "") or "(no prefix)"
    return "unknown", ""


def _rule_agents(rule_info):
    """List of agent_name(s) a dispatch rule dispatches to via room_config.agents.
    Empty list => the rule has NO explicit agent dispatch (only an automatic-dispatch
    worker — one registered with no agent_name — would ever pick the room up)."""
    rc = getattr(rule_info, "room_config", None)
    if not rc:
        return []
    return [getattr(a, "agent_name", "") for a in getattr(rc, "agents", [])]


def _matches_number(trunk, number: str) -> bool:
    nums = list(getattr(trunk, "numbers", []) or [])
    return (not nums) or (number in nums)


def _rule_applies_to_trunk(rule_info, trunk_id: str) -> bool:
    tids = list(getattr(rule_info, "trunk_ids", []) or [])
    return (not tids) or (trunk_id in tids)


async def main():
    number = sys.argv[1] if len(sys.argv) > 1 else (settings.TWILIO_PHONE_NUMBER or "")
    print("=" * 72)
    print("LiveKit SIP — READ-ONLY inspection (no changes made)")
    print(f"LIVEKIT_URL = {settings.LIVEKIT_URL}")
    print(f"Worker registers as agent_name = {settings.AGENT_NAME!r}")
    print(f"Analyzing routing for dialed number = {number!r}")
    print("=" * 72)

    lk = api.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        trunks = (await lk.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())).items
        rules = (await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())).items

        print(f"\n── INBOUND SIP TRUNKS ({len(trunks)}) " + "─" * 40)
        if not trunks:
            print("  (none) ⚠️  no inbound trunk — inbound SIP calls cannot be accepted")
        for t in trunks:
            nums = list(getattr(t, "numbers", []) or [])
            print(f"\n  trunk_id : {t.sip_trunk_id}")
            print(f"  name     : {t.name!r}")
            print(f"  numbers  : {nums or '[] (accepts ANY dialed number)'}")
            print(f"  allowed_numbers   : {list(getattr(t, 'allowed_numbers', []) or []) or '[] (any caller)'}")
            print(f"  allowed_addresses : {list(getattr(t, 'allowed_addresses', []) or []) or '[] (any IP)'}")
            print(f"  krisp_enabled     : {getattr(t, 'krisp_enabled', None)}")

        print(f"\n── DISPATCH RULES ({len(rules)}) " + "─" * 44)
        if not rules:
            print("  (none) ⚠️  no dispatch rule — an accepted call creates no room/agent")
        for r in rules:
            kind, prefix = _rule_kind_and_prefix(r)
            agents = _rule_agents(r)
            tids = list(getattr(r, "trunk_ids", []) or [])
            print(f"\n  rule_id   : {r.sip_dispatch_rule_id}")
            print(f"  name      : {r.name!r}")
            print(f"  type      : {kind}  (room prefix/name: {prefix})")
            print(f"  trunk_ids : {tids or '[] (applies to ALL trunks)'}")
            print(f"  room_preset : {getattr(r, 'room_preset', '') or '(none)'}")
            if agents:
                print(f"  ➜ DISPATCHES TO AGENT(S): {agents}")
            else:
                print("  ➜ NO agent dispatch configured (room_config.agents empty) — "
                      "ONLY an automatic-dispatch worker (no agent_name) would be offered "
                      "this room. An explicit 'clinic-agent' worker would NOT.")

        # ── Routing analysis for the dialed number ───────────────────────────────
        print("\n" + "=" * 72)
        print(f"ROUTING ANALYSIS for dialed number {number!r}")
        print("=" * 72)
        accepting = [t for t in trunks if _matches_number(t, number)]
        if not accepting:
            print("❌ No inbound trunk accepts this number → LiveKit rejects the INVITE, "
                  "no room is created, the worker is never called.")
        for t in accepting:
            print(f"\n✅ Trunk {t.sip_trunk_id} ({t.name!r}) accepts {number!r}.")
            applicable = [r for r in rules if _rule_applies_to_trunk(r, t.sip_trunk_id)]
            if not applicable:
                print("   ❌ but NO dispatch rule applies to this trunk → no room/agent created.")
            for r in applicable:
                kind, prefix = _rule_kind_and_prefix(r)
                agents = _rule_agents(r)
                print(f"   → rule {r.sip_dispatch_rule_id} ({kind}, prefix {prefix}) "
                      f"dispatches to: {agents or 'NO AGENT (automatic only)'}")
                if settings.AGENT_NAME and agents and settings.AGENT_NAME not in agents:
                    print(f"      ⚠️ MISMATCH: worker is {settings.AGENT_NAME!r} but rule "
                          f"targets {agents} → no job reaches the worker.")
                elif settings.AGENT_NAME and not agents:
                    print(f"      ⚠️ MISMATCH: worker uses EXPLICIT dispatch "
                          f"({settings.AGENT_NAME!r}) but rule has NO agent → no job "
                          "reaches the worker. Fix: give the rule "
                          f"RoomAgentDispatch(agent_name={settings.AGENT_NAME!r}) "
                          "(run scripts/fix_dispatch_rule.py), or set AGENT_NAME='' for "
                          "automatic dispatch.")
                elif settings.AGENT_NAME and settings.AGENT_NAME in agents:
                    print(f"      ✅ MATCH: rule dispatches to {settings.AGENT_NAME!r} "
                          "(same as the worker).")
        print("\nDone — nothing was modified.")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(main())

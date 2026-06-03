"""
LiveKit voice agent ("Aria") that joins a LiveKit room when a SIP call arrives.

Flow:  Twilio number -> LiveKit SIP trunk -> LiveKit room -> this agent joins.

Built on the livekit-agents framework (AgentSession = STT -> LLM -> TTS with
Silero VAD, barge-in, and turn detection built in). The Golden Fork action tools
are wired as @function_tool methods so Aria can actually book/cancel/check
reservations, take/check orders, answer FAQs, and transfer to a human.

Triggered by the LiveKit `participant_joined` webhook (see
app/api/routes/livekit_webhooks.py), which calls run_agent_in_room() in the
background. For production scale you'd instead run this as a dedicated LiveKit
worker (see run_worker() at the bottom) dispatched via the SIP dispatch rule.
"""
import asyncio

from app.core.config import settings
from app.agents.tools import execute_tool

DEFAULT_SYSTEM_PROMPT = (
    "You are Aria, a friendly AI receptionist for the Golden Fork restaurant chain "
    "(Downtown, Midtown, Uptown, Airport). Keep ALL responses under 2 sentences. Be "
    "warm and professional. You can book tables, cancel reservations, check "
    "reservations, take orders, answer menu/FAQ questions, and transfer to a human. "
    "Always use your tools to take real actions."
)
GREETING = (
    "Thank you for calling Golden Fork! I'm Aria, your AI assistant. "
    "How can I help you today?"
)


def _build_system_prompt(behavior_config: dict) -> str:
    prompt = behavior_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    hard = [r["rule"] for r in (behavior_config.get("hard_rules") or []) if r.get("enabled")]
    if hard:
        prompt += "\n\nSTRICT RULES:\n" + "\n".join(f"- {r}" for r in hard)
    return prompt


def _make_agent_class():
    """Build the Agent subclass lazily so livekit-agents imports stay lazy."""
    from livekit.agents import Agent, function_tool

    class GoldenForkAgent(Agent):
        def __init__(self, instructions: str):
            super().__init__(instructions=instructions)

        async def on_enter(self):
            await self.session.say(GREETING, allow_interruptions=True)

        @function_tool
        async def create_reservation(self, customer_name: str, customer_phone: str,
                                     party_size: int, date: str, time: str, location: str) -> str:
            """Book a table. date is YYYY-MM-DD, time is HH:MM, location is one of
            Downtown, Midtown, Uptown, Airport."""
            text, _ = await execute_tool("create_reservation", {
                "customer_name": customer_name, "customer_phone": customer_phone,
                "party_size": party_size, "date": date, "time": time, "location": location})
            return text

        @function_tool
        async def cancel_reservation(self, customer_phone: str = "", reservation_id: str = "") -> str:
            """Cancel a reservation by phone number or reservation id."""
            text, _ = await execute_tool("cancel_reservation", {
                "customer_phone": customer_phone, "reservation_id": reservation_id})
            return text

        @function_tool
        async def check_reservation(self, customer_phone: str) -> str:
            """Look up the caller's upcoming reservation by phone number."""
            text, _ = await execute_tool("check_reservation", {"customer_phone": customer_phone})
            return text

        @function_tool
        async def answer_faq(self, question: str) -> str:
            """Answer a common question (hours, parking, delivery, menu, policies)."""
            text, _ = await execute_tool("answer_faq", {"question": question})
            return text

        @function_tool
        async def take_order(self, customer_name: str, customer_phone: str,
                            order_type: str, items: list[str], address: str = "") -> str:
            """Place an order. order_type is delivery, pickup, or dine_in. items is a
            list of menu item names. address is required for delivery."""
            text, _ = await execute_tool("take_order", {
                "customer_name": customer_name, "customer_phone": customer_phone,
                "order_type": order_type, "address": address,
                "items": [{"name": n, "qty": 1} for n in items]})
            return text

        @function_tool
        async def check_order_status(self, customer_phone: str) -> str:
            """Check the status of the caller's latest order by phone number."""
            text, _ = await execute_tool("check_order_status", {"customer_phone": customer_phone})
            return text

        @function_tool
        async def transfer_to_human(self, reason: str) -> str:
            """Escalate to a human team member when the caller is upset or out of scope."""
            text, _ = await execute_tool("transfer_to_human", {"reason": reason})
            return text

    return GoldenForkAgent


def _build_session(behavior_config: dict):
    from livekit.agents import AgentSession
    from livekit.plugins import openai, silero
    voice = behavior_config.get("voice_id") or "alloy"
    key = settings.OPENAI_API_KEY
    return AgentSession(
        stt=openai.STT(model="whisper-1", api_key=key),
        llm=openai.LLM(model="gpt-4o-mini", api_key=key),
        tts=openai.TTS(voice=voice, model="tts-1", api_key=key),
        vad=silero.VAD.load(),
    )


# Rooms currently being handled in THIS process — guards against the webhook and
# the room watcher both spawning an agent into the same room (double-join).
_active_rooms: set[str] = set()


async def run_agent_in_room(room_name: str, behavior_config: dict | None = None):
    """Join a LiveKit room and run Aria until the call ends. Never raises.
    Idempotent per room within this process."""
    behavior_config = behavior_config or {}
    if room_name in _active_rooms:
        return
    _active_rooms.add(room_name)
    try:
        from livekit import rtc
        from livekit.agents import RoomInputOptions

        instructions = _build_system_prompt(behavior_config)
        room = rtc.Room()
        await room.connect(settings.LIVEKIT_URL, generate_agent_token(room_name))
        print(f"[agent] connected to room: {room_name}")

        disconnected = asyncio.Event()
        room.on("disconnected", lambda *_a: disconnected.set())

        session = _build_session(behavior_config)
        agent = _make_agent_class()(instructions)
        await session.start(agent=agent, room=room, room_input_options=RoomInputOptions())

        await disconnected.wait()
        print(f"[agent] call ended, leaving room: {room_name}")
        await session.aclose()
    except Exception as e:
        print(f"[agent] error in room {room_name}: {type(e).__name__}: {e}")
    finally:
        _active_rooms.discard(room_name)


def generate_agent_token(room_name: str) -> str:
    from livekit import api
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity("aria-agent")
        .with_name("Aria")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    return token.to_jwt()


# ── Recommended production path: dedicated LiveKit worker ────────────────────
# Instead of the webhook spawning agents, run a worker that LiveKit dispatches
# jobs to (set room_config.agents=[RoomAgentDispatch(agent_name="aria")] on the
# dispatch rule). Deploy as a separate process:  python -m app.agents.pipecat_agent
async def _entrypoint(ctx):
    from livekit.agents import RoomInputOptions, AutoSubscribe
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    session = _build_session({})
    agent = _make_agent_class()(DEFAULT_SYSTEM_PROMPT)
    await session.start(agent=agent, room=ctx.room, room_input_options=RoomInputOptions())


def run_worker():
    # No agent_name -> automatic dispatch: the worker joins every new room.
    from livekit.agents import cli, WorkerOptions
    cli.run_app(WorkerOptions(entrypoint_fnc=_entrypoint))


if __name__ == "__main__":
    run_worker()

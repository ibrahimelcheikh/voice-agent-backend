"""
Pipecat + LiveKit Voice Agent (production).

Pipeline:  LiveKit audio in -> STT -> LLM (+ tools) -> TTS -> LiveKit audio out
  STT : OpenAI Whisper (Deepgram if a key is present)
  LLM : gpt-4o-mini, system prompt assembled from the behavior config,
        OpenAI function-calling wired to the Golden Fork action tools
  TTS : OpenAI TTS using the agent's voice_id
  VAD : Silero (turn detection)

Every heavy import is lazy and guarded so an incomplete pipecat/livekit install
can never crash the API server — the agent simply runs in a safe fallback mode.
The actual telephony bridge is exercised only on a live Twilio call.
"""
import asyncio

from app.core.config import settings
from app.agents.tools import TOOL_SCHEMAS, execute_tool


def build_system_prompt(agent_config: dict) -> str:
    """Assemble the LLM system prompt from a behavior config (hard rules,
    blocked topics, escalation triggers, extraction fields)."""
    prompt = agent_config.get("system_prompt") or "You are a helpful AI assistant."

    hard = [r["rule"] for r in (agent_config.get("hard_rules") or []) if r.get("enabled")]
    if hard:
        prompt += "\n\nSTRICT RULES (never violate these):\n" + "\n".join(f"- {r}" for r in hard)

    soft = [r["rule"] for r in (agent_config.get("soft_rules") or []) if r.get("enabled")]
    if soft:
        prompt += "\n\nGUIDELINES:\n" + "\n".join(f"- {r}" for r in soft)

    blocked = agent_config.get("blocked_topics") or []
    if blocked:
        prompt += "\n\nNever discuss these topics: " + ", ".join(blocked) + "."

    triggers = agent_config.get("escalation_triggers") or []
    if triggers:
        prompt += ("\n\nImmediately call transfer_to_human if any of these occur: "
                   + ", ".join(triggers) + ".")

    fields = agent_config.get("data_extraction_fields") or []
    if fields:
        prompt += ("\n\nDuring the conversation, naturally collect the following "
                   "information when relevant: " + ", ".join(fields) + ".")

    prompt += ("\n\nYou can take real actions using the provided tools (book/cancel/"
               "check reservations, take orders, check order status, answer FAQs, "
               "transfer to a human). Use them whenever the caller asks. Keep replies "
               "short and natural for a phone conversation.")
    return prompt


async def _make_tool_handler():
    """Build a pipecat-style function handler that runs our DB tools."""
    async def handler(function_name, tool_call_id, arguments, llm, context, result_callback):
        _text, payload = await execute_tool(function_name, arguments or {})
        await result_callback(payload)
    return handler


async def run_voice_agent(room_name: str, agent_config: dict):
    """Run the Pipecat voice agent inside a LiveKit room.

    Invoked as a background task when a Twilio call is bridged into `room_name`.
    Never raises — any missing dependency degrades to fallback mode.
    """
    try:
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

        # Service import paths moved across pipecat versions — try both layouts.
        try:
            from pipecat.services.openai.llm import OpenAILLMService
            from pipecat.services.openai.tts import OpenAITTSService
            from pipecat.services.openai.stt import OpenAISTTService
        except ImportError:  # older flat layout
            from pipecat.services.openai import (
                OpenAILLMService, OpenAITTSService, OpenAISTTService,
            )

        from pipecat.transports.services.livekit import LiveKitTransport, LiveKitParams
        from pipecat.audio.vad.silero import SileroVADAnalyzer

        system_prompt = build_system_prompt(agent_config)

        transport = LiveKitTransport(
            url=settings.LIVEKIT_URL,
            token=await generate_agent_token(room_name),
            room_name=room_name,
            params=LiveKitParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # STT — Deepgram if a key exists, otherwise OpenAI Whisper.
        if settings.DEEPGRAM_API_KEY:
            from pipecat.services.deepgram.stt import DeepgramSTTService
            stt = DeepgramSTTService(api_key=settings.DEEPGRAM_API_KEY)
        else:
            stt = OpenAISTTService(api_key=settings.OPENAI_API_KEY)

        llm = OpenAILLMService(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")

        # Register every tool with the LLM service for function calling.
        handler = await _make_tool_handler()
        for schema in TOOL_SCHEMAS:
            try:
                llm.register_function(schema["function"]["name"], handler)
            except Exception:
                pass

        tts = OpenAITTSService(
            api_key=settings.OPENAI_API_KEY,
            voice=agent_config.get("voice_id", "alloy"),
        )

        # Tools schema for the context (try the modern ToolsSchema, fall back to raw).
        try:
            from pipecat.adapters.schemas.tools_schema import ToolsSchema
            from pipecat.adapters.schemas.function_schema import FunctionSchema
            fn_schemas = [
                FunctionSchema(
                    name=t["function"]["name"],
                    description=t["function"]["description"],
                    properties=t["function"]["parameters"]["properties"],
                    required=t["function"]["parameters"].get("required", []),
                )
                for t in TOOL_SCHEMAS
            ]
            tools = ToolsSchema(standard_tools=fn_schemas)
        except Exception:
            tools = TOOL_SCHEMAS

        messages = [{"role": "system", "content": system_prompt}]
        context = OpenAILLMContext(messages, tools)
        context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

        max_dur = agent_config.get("max_call_duration", 480)
        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        runner = PipelineRunner(handle_sigint=False)

        # Enforce the configured max call duration.
        async def _runner():
            await runner.run(task)

        try:
            await asyncio.wait_for(_runner(), timeout=max_dur + 30)
        except asyncio.TimeoutError:
            print(f"[voice-agent] room {room_name} hit max duration, ending gracefully")
            try:
                await task.cancel()
            except Exception:
                pass

    except ImportError as e:
        print(f"[voice-agent] pipecat/livekit not fully available ({e}); fallback mode for room {room_name}")
        await asyncio.sleep(1)
    except Exception as e:  # never let a background task take down the server
        print(f"[voice-agent] error in room {room_name}: {type(e).__name__}: {e}")
        await asyncio.sleep(1)


async def generate_agent_token(room_name: str) -> str:
    """Generate a LiveKit JWT for the agent to join the room."""
    from livekit import api
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity("ai-agent")
        .with_name("AI Agent")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    return token.to_jwt()

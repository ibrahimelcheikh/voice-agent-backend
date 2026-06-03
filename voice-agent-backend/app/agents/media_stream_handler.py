"""
Twilio Media Streams handler — built on a proper Pipecat pipeline.

Unlike the previous manual loop, Pipecat provides the hard parts natively:
  * Silero VAD (voice activity detection)
  * barge-in / interruption (allow_interruptions=True)
  * turn detection + natural conversation flow

Pipeline:  Twilio µ-law in → STT → LLM (+Golden Fork tools) → TTS → Twilio µ-law out
The TwilioFrameSerializer handles the µ-law(8k) ↔ PCM conversion, so we don't.

IMPORTANT: TwilioFrameSerializer needs the real `streamSid`, which only arrives
in the WebSocket's first "start" message — so we read the handshake before
building the transport.
"""
import json

from fastapi import WebSocket

from app.core.config import settings
from app.agents.tools import TOOL_SCHEMAS, execute_tool

DEFAULT_SYSTEM_PROMPT = (
    "You are Aria, a friendly AI receptionist for the Golden Fork restaurant chain "
    "(Downtown, Midtown, Uptown, Airport). Keep responses under 2 sentences. Be warm "
    "and professional. You can book tables, answer questions, take orders, and cancel "
    "reservations — use your tools to take real actions."
)
GREETING = (
    "Thank you for calling Golden Fork. I'm Aria, your AI assistant. "
    "How can I help you today?"
)


async def _read_twilio_start(websocket: WebSocket):
    """Consume the initial Twilio frames and return (stream_sid, call_sid)."""
    async for message in websocket.iter_text():
        data = json.loads(message)
        if data.get("event") == "start":
            start = data["start"]
            call_sid = start.get("callSid") or start.get("customParameters", {}).get("callSid")
            return start["streamSid"], call_sid
        # ignore the preceding "connected" event
    return None, None


async def handle_media_stream(websocket: WebSocket, behavior_config: dict | None = None):
    behavior_config = behavior_config or {}

    # 1) Handshake first so the serializer gets the real streamSid.
    stream_sid, call_sid = await _read_twilio_start(websocket)
    if not stream_sid:
        await websocket.close()
        return

    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.transports.network.fastapi_websocket import (
        FastAPIWebsocketTransport, FastAPIWebsocketParams,
    )
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams
    from pipecat.services.openai.llm import OpenAILLMService, OpenAILLMContext
    from pipecat.services.openai.stt import OpenAISTTService
    from pipecat.services.openai.tts import OpenAITTSService
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.adapters.schemas.tools_schema import ToolsSchema
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.frames.frames import TTSSpeakFrame

    system_prompt = behavior_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    voice_id = behavior_config.get("voice_id") or "alloy"

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8)),
            vad_audio_passthrough=True,
            serializer=serializer,
        ),
    )

    stt = OpenAISTTService(api_key=settings.OPENAI_API_KEY, model="whisper-1")
    llm = OpenAILLMService(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")
    tts = OpenAITTSService(api_key=settings.OPENAI_API_KEY, voice=voice_id, model="tts-1")

    # Wire the Golden Fork action tools into the LLM (function calling).
    async def _tool_handler(params):
        _text, payload = await execute_tool(params.function_name, params.arguments or {})
        await params.result_callback(payload)

    fn_schemas = []
    for t in TOOL_SCHEMAS:
        fn = t["function"]
        llm.register_function(fn["name"], _tool_handler)
        fn_schemas.append(FunctionSchema(
            name=fn["name"],
            description=fn["description"],
            properties=fn["parameters"]["properties"],
            required=fn["parameters"].get("required", []),
        ))
    tools = ToolsSchema(standard_tools=fn_schemas)

    messages = [{"role": "system", "content": system_prompt}]
    context = OpenAILLMContext(messages, tools=tools)
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

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True, enable_metrics=False),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        # Speak the greeting immediately (deterministic, no LLM latency).
        await task.queue_frames([TTSSpeakFrame(GREETING)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)  # required: not main thread / Windows
    try:
        await runner.run(task)
    except Exception as e:  # never let a dropped call bubble up
        print(f"[media-stream] pipeline error (call {call_sid}): {type(e).__name__}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass

"""
Handles the Twilio Media Streams WebSocket.

Twilio sends/receives audio as base64 **G.711 µ-law, 8 kHz, mono, 20 ms frames**
(160 bytes each). Pipeline per call:

    Twilio µ-law in  ->  WAV(PCM16 8k)  ->  Whisper STT
                      ->  GPT-4o-mini (+ Golden Fork tools, per-call memory)
                      ->  OpenAI TTS (pcm 24k)  ->  resample 8k + µ-law  ->  Twilio out

Notes on the audio (this is where naive implementations go silent):
  * OpenAI TTS has NO "ulaw" format — we request `pcm` (24 kHz/16-bit/mono) and
    convert to 8 kHz µ-law with the stdlib `audioop` module (Python 3.11).
  * Whisper cannot read raw µ-law bytes — we decode µ-law -> PCM16 and wrap it
    in a real WAV header before uploading.
"""
import asyncio
import base64
import io
import json
import wave

from fastapi import WebSocket
from openai import AsyncOpenAI

from app.core.config import settings
from app.agents.tools import TOOL_SCHEMAS, execute_tool

try:
    import audioop  # stdlib (Python <=3.12); present on 3.11
except Exception:  # pragma: no cover
    audioop = None

TWILIO_RATE = 8000          # Twilio µ-law sample rate
OPENAI_TTS_RATE = 24000     # OpenAI "pcm" output rate
FRAMES_BEFORE_STT = 100     # 100 * 20 ms ≈ 2 s of audio before we transcribe
OUT_CHUNK = 8000            # ~1 s of µ-law per outbound media message

SYSTEM_PROMPT = (
    "You are Aria, an AI receptionist for the Golden Fork restaurant chain "
    "(Downtown, Midtown, Uptown, Airport). You can book and cancel tables, check "
    "reservations, take and check orders, answer FAQs, and transfer to a human. "
    "Use your tools to take real actions. Always be warm, professional, and concise — "
    "keep spoken responses to 1-2 short sentences."
)

# Per-call conversation memory: call_sid -> list[messages]
_HISTORY: dict[str, list] = {}


async def handle_media_stream(websocket: WebSocket):
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    stream_sid = None
    call_sid = None
    audio_buffer: list[str] = []

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid") or data["start"].get("customParameters", {}).get("callSid")
                _HISTORY[call_sid] = [{"role": "system", "content": SYSTEM_PROMPT}]
                print(f"[media-stream] started {stream_sid} (call {call_sid})")

                greeting = await text_to_speech(
                    "Thank you for calling Golden Fork. I'm Aria, your AI assistant. "
                    "How can I help you today?",
                    client,
                )
                await send_audio(websocket, stream_sid, greeting)

            elif event == "media":
                audio_buffer.append(data["media"]["payload"])

                if len(audio_buffer) >= FRAMES_BEFORE_STT:
                    mulaw = b"".join(base64.b64decode(c) for c in audio_buffer)
                    audio_buffer = []

                    transcript = await speech_to_text(mulaw, client)
                    if transcript and len(transcript.strip()) > 2:
                        print(f"[media-stream] caller: {transcript}")
                        response_text = await get_ai_response(transcript, call_sid)
                        print(f"[media-stream] Aria: {response_text}")
                        audio_response = await text_to_speech(response_text, client)
                        await send_audio(websocket, stream_sid, audio_response)

            elif event == "stop":
                print(f"[media-stream] stopped {stream_sid}")
                break

    except Exception as e:
        print(f"[media-stream] error: {type(e).__name__}: {e}")
    finally:
        _HISTORY.pop(call_sid, None)


async def speech_to_text(mulaw_data: bytes, client: AsyncOpenAI) -> str:
    """Decode µ-law -> PCM16, wrap in WAV, send to Whisper."""
    if not mulaw_data or audioop is None:
        return ""
    try:
        pcm16 = audioop.ulaw2lin(mulaw_data, 2)  # 8 kHz, 16-bit
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(TWILIO_RATE)
            wav.writeframes(pcm16)
        buf.seek(0)
        buf.name = "audio.wav"
        transcript = await client.audio.transcriptions.create(
            model="whisper-1", file=buf, language="en",
        )
        return transcript.text
    except Exception as e:
        print(f"[media-stream] STT error: {e}")
        return ""


async def text_to_speech(text: str, client: AsyncOpenAI) -> bytes:
    """Synthesize speech and return 8 kHz µ-law bytes for Twilio."""
    if not text:
        return b""
    try:
        resp = await client.audio.speech.create(
            model="tts-1", voice="alloy", input=text,
            response_format="pcm",  # raw 24 kHz / 16-bit / mono PCM
        )
        pcm24 = resp.content
        if audioop is None:
            return b""
        pcm8, _ = audioop.ratecv(pcm24, 2, 1, OPENAI_TTS_RATE, TWILIO_RATE, None)
        return audioop.lin2ulaw(pcm8, 2)
    except Exception as e:
        print(f"[media-stream] TTS error: {e}")
        return b""


async def get_ai_response(user_message: str, call_sid: str) -> str:
    """LLM turn with per-call memory and the Golden Fork action tools."""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    history = _HISTORY.setdefault(call_sid, [{"role": "system", "content": SYSTEM_PROMPT}])
    history.append({"role": "user", "content": user_message})
    try:
        for _ in range(4):
            resp = await client.chat.completions.create(
                model="gpt-4o-mini", messages=history,
                tools=TOOL_SCHEMAS, tool_choice="auto", max_tokens=120,
            )
            msg = resp.choices[0].message
            if msg.tool_calls:
                history.append({
                    "role": "assistant", "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result_text, payload = await execute_tool(tc.function.name, args)
                    history.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": json.dumps({"result": result_text, **payload}),
                    })
                continue
            reply = (msg.content or "I'm sorry, could you repeat that?").strip()
            history.append({"role": "assistant", "content": reply})
            return reply
        return "Let me get a team member to help you with that."
    except Exception as e:
        print(f"[media-stream] LLM error: {e}")
        return "I'm sorry, could you please repeat that?"


async def send_audio(websocket: WebSocket, stream_sid: str, mulaw_audio: bytes):
    """Send µ-law audio back to Twilio in modest chunks."""
    if not mulaw_audio or not stream_sid:
        return
    for i in range(0, len(mulaw_audio), OUT_CHUNK):
        chunk = mulaw_audio[i:i + OUT_CHUNK]
        await websocket.send_json({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode("utf-8")},
        })
        await asyncio.sleep(0)  # yield to the event loop

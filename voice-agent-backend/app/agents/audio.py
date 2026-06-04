"""
Prerecorded audio for the clinic agent (FILE 6).

On startup we generate three short clips with OpenAI TTS (if they don't already
exist) and cache them under app/audio/ as both .mp3 (portable) and .pcm
(raw 24kHz/16-bit/mono — what the LiveKit output transport plays directly):

  * greeting — played the instant a caller connects (faster than live TTS)
  * goodbye  — played right before we hang up
  * thinking — short "one moment" filler

Playing the prerecorded greeting/goodbye is faster and more consistent than
generating speech live every call.
"""
import os
import asyncio

from app.core.config import settings

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio")

# OpenAI "pcm" output is always 24kHz, 16-bit signed, mono, little-endian.
SAMPLE_RATE = 24000
NUM_CHANNELS = 1
_FRAME_MS = 20
_BYTES_PER_FRAME = int(SAMPLE_RATE * (_FRAME_MS / 1000.0)) * 2 * NUM_CHANNELS  # 960

CLIPS = {
    "greeting": "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?",
    "goodbye": "Thank you for calling, have a great day!",
    "thinking": "One moment please, let me check that for you.",
}


def _pcm_path(name: str) -> str:
    return os.path.join(AUDIO_DIR, f"{name}.pcm")


def _mp3_path(name: str) -> str:
    return os.path.join(AUDIO_DIR, f"{name}.mp3")


async def ensure_audio_files(voice: str = "shimmer", clips: dict | None = None):
    """Generate any missing clips with OpenAI TTS. Safe to call on every boot."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    clips = clips or CLIPS
    if not settings.OPENAI_API_KEY:
        print("[audio] OPENAI_API_KEY not set — skipping prerecorded audio generation")
        return
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    for name, text in clips.items():
        if os.path.exists(_pcm_path(name)):
            continue
        try:
            await _generate(client, name, text, voice)
            print(f"[audio] generated clip: {name}")
        except Exception as e:
            print(f"[audio] could not generate {name}: {type(e).__name__}: {e}")


async def _generate(client, name: str, text: str, voice: str):
    # MP3 for portability...
    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts", voice=voice, input=text, response_format="mp3",
    ) as resp:
        await resp.stream_to_file(_mp3_path(name))
    # ...and raw PCM for direct, decode-free playback through the transport.
    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts", voice=voice, input=text, response_format="pcm",
    ) as resp:
        await resp.stream_to_file(_pcm_path(name))


def load_pcm(name: str) -> bytes:
    path = _pcm_path(name)
    if not os.path.exists(path):
        return b""
    with open(path, "rb") as f:
        return f.read()


async def play_clip(task, name: str):
    """Stream a prerecorded clip into a running PipelineTask as 20ms audio frames.

    Falls back to live TTS (TTSSpeakFrame) if the prerecorded clip is missing."""
    from pipecat.frames.frames import OutputAudioRawFrame, TTSSpeakFrame

    pcm = load_pcm(name)
    if not pcm:
        await task.queue_frame(TTSSpeakFrame(text=CLIPS.get(name, "")))
        return

    frames = []
    for i in range(0, len(pcm), _BYTES_PER_FRAME):
        chunk = pcm[i:i + _BYTES_PER_FRAME]
        frames.append(OutputAudioRawFrame(
            audio=chunk, sample_rate=SAMPLE_RATE, num_channels=NUM_CHANNELS))
    await task.queue_frames(frames)


def clip_duration_seconds(name: str) -> float:
    return len(load_pcm(name)) / (SAMPLE_RATE * 2 * NUM_CHANNELS)

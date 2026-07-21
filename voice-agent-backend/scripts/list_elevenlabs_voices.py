"""
List ElevenLabs library voices (id + name + labels) so you can pick exact voice ids for
ELEVENLABS_VOICE_ID_EN / ELEVENLABS_VOICE_ID_AR. Mirrors list_cartesia_arabic_voices.py.

We never guess a voice id — run this with your key and copy the id you want.

Usage:
    ELEVENLABS_API_KEY=sk_... python -m scripts.list_elevenlabs_voices          # all your voices
    ELEVENLABS_API_KEY=sk_... python -m scripts.list_elevenlabs_voices arabic   # filter by substring
"""
import os
import sys
import urllib.request
import json

from app.core.config import settings


def main():
    key = os.environ.get("ELEVENLABS_API_KEY") or settings.ELEVENLABS_API_KEY
    if not key:
        print("Set ELEVENLABS_API_KEY first.")
        sys.exit(2)
    needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()

    # v2 lists shared/library voices with rich metadata; v1 lists the voices on your account.
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    voices = data.get("voices", [])
    print(f"{len(voices)} voices on your account "
          f"(add library voices at elevenlabs.io/app/voice-library, then re-run):\n")
    for v in voices:
        labels = v.get("labels", {}) or {}
        gender = labels.get("gender", "")
        accent = labels.get("accent", "")
        desc = labels.get("description", "")
        blob = f"{v.get('name','')} {gender} {accent} {desc} {v.get('category','')}".lower()
        if needle and needle not in blob:
            continue
        print(f"  {v.get('voice_id')}  |  {v.get('name'):<18}  {gender:<8} {accent:<12} {desc}")


if __name__ == "__main__":
    main()

"""
List Cartesia voices that support Arabic, so a CONFIRMED Modern-Standard-Arabic voice id
can be chosen for CARTESIA_AR_VOICE (Phase 3b). We never guess a voice id — run this with
your Cartesia key (it lives in Railway, so run it there or export it locally) and pick one:

    CARTESIA_API_KEY=sk_car_... python scripts/list_cartesia_arabic_voices.py

Then set CARTESIA_AR_VOICE to the chosen id (Railway var). sonic-2 does NOT support Arabic;
CARTESIA_AR_MODEL defaults to sonic-3.5, which does (language code 'ar').

Prints each Arabic voice's id, name, language, and description. Read-only — lists only.
"""
import json
import os
import urllib.parse
import urllib.request

from app.core.config import settings

API = "https://api.cartesia.ai/voices"
VERSION = "2026-03-01"


def _fetch(key: str, language: str = "ar") -> list[dict]:
    voices: list[dict] = []
    url = f"{API}?{urllib.parse.urlencode({'language': language, 'limit': 100})}"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {key}",
            "Cartesia-Version": VERSION,
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
        # Response shape: {"data": [...], "has_more": bool, "next_page": <token|url>}
        batch = payload.get("data", payload if isinstance(payload, list) else [])
        voices.extend(batch)
        nxt = payload.get("next_page") if isinstance(payload, dict) else None
        if payload.get("has_more") and nxt:
            url = nxt if str(nxt).startswith("http") else \
                f"{API}?{urllib.parse.urlencode({'language': language, 'limit': 100, 'starting_after': nxt})}"
        else:
            url = None
    return voices


def main() -> None:
    key = os.environ.get("CARTESIA_API_KEY") or settings.CARTESIA_API_KEY
    if not key:
        print("No CARTESIA_API_KEY available. Export it or run where it is configured (Railway).")
        return
    voices = _fetch(key, "ar")
    if not voices:
        print("No Arabic voices returned. Check the key, or browse play.cartesia.ai/voices.")
        return
    print(f"Arabic-capable Cartesia voices ({len(voices)}):\n")
    for v in voices:
        print(f"  id={v.get('id')}  name={v.get('name')!r}  language={v.get('language')}")
        desc = (v.get("description") or "").strip()
        if desc:
            print(f"      {desc[:120]}")
    print("\nSet CARTESIA_AR_VOICE to the id of the MSA voice you prefer (Railway var).")


if __name__ == "__main__":
    main()

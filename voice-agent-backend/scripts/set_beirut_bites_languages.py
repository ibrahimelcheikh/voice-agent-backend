"""
Set Beirut Bites' supported_languages to ["en", "ar"] on the LIVE tenant record, so the
Phase 3a DTMF language prompt fires for its Twilio number (+16575347796).

Beirut Bites (id 8b473b5d-5665-4c7f-9a8a-8488e4c534dd) is a PRODUCTION-only tenant — it
was created via the API, not by seed.py — so this updates the live row directly through
the (unauthenticated) tenant-update endpoint, which is the exact record the agent reads at
call time. Editing the seed function would NOT change the already-persisted row, which is
why this hits the running API instead.

It changes ONLY supported_languages on ONLY this one tenant. Idempotent: re-running simply
re-asserts ["en", "ar"]. The phone number, other tenants, and all other fields are left
untouched.

    python scripts/set_beirut_bites_languages.py                 # uses settings.PUBLIC_URL
    BASE_URL=http://localhost:8030 python scripts/set_beirut_bites_languages.py   # override
"""
import json
import os
import urllib.request

from app.core.config import settings

TENANT_ID = "8b473b5d-5665-4c7f-9a8a-8488e4c534dd"  # Beirut Bites (+16575347796)
LANGUAGES = ["en", "ar"]                            # en first = primary/default


def _get(base: str) -> dict:
    with urllib.request.urlopen(f"{base}/tenants/{TENANT_ID}", timeout=30) as r:
        return json.load(r)["data"]


def _patch(base: str) -> None:
    body = json.dumps({"supported_languages": LANGUAGES}).encode()
    req = urllib.request.Request(f"{base}/tenants/{TENANT_ID}", data=body, method="PATCH",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        json.load(r)


def main() -> None:
    base = (os.environ.get("BASE_URL") or settings.PUBLIC_URL).rstrip("/")
    print(f"API base: {base}")
    before = _get(base)
    print(f"BEFORE: {before['business_name']} ({before['twilio_phone_number']}) "
          f"supported_languages={before['supported_languages']}")
    _patch(base)
    after = _get(base)
    print(f"AFTER : {after['business_name']} ({after['twilio_phone_number']}) "
          f"supported_languages={after['supported_languages']}")
    assert after["supported_languages"] == LANGUAGES, "update did not take"
    print("OK — Beirut Bites is multi-language; the DTMF language prompt will fire.")


if __name__ == "__main__":
    main()

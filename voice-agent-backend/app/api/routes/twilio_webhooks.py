"""
Twilio Webhooks — This is where real phone calls come in
"""
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, CallOutcome
from app.core.config import settings
from datetime import datetime

router = APIRouter()


def _livekit_sip_host() -> str:
    """Project SIP host derived from LIVEKIT_URL.
    wss://<proj>.livekit.cloud -> <proj>.sip.livekit.cloud
    (verify in LiveKit Dashboard → Settings → SIP)."""
    host = settings.LIVEKIT_URL.replace("wss://", "").replace("ws://", "").rstrip("/")
    return host.replace(".livekit.cloud", ".sip.livekit.cloud")


def _sip_dial_twiml(called_number: str | None = None, language: str | None = None) -> str:
    """TwiML that dials the call into the LiveKit SIP trunk. The DIALED number becomes
    the SIP user part so LiveKit carries it as the trunk/called number — that is the
    phone -> tenant routing key the agent reads when it joins the `call-<random>` room.

    When `language` is set (the caller's IVR choice), it is threaded to the agent as a
    custom SIP header `X-Language`, which LiveKit surfaces as a participant attribute the
    agent reads. It is purely additive: a direct-SIP call (no IVR) carries no header, and
    the agent then defaults to English — so this path stays reversible and English-safe."""
    number = called_number or settings.TWILIO_PHONE_NUMBER
    sip_uri = f"sip:{number}@{_livekit_sip_host()};transport=tcp"
    if language:
        sip_uri += f"?X-Language={language}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{sip_uri}</Sip>
    </Dial>
</Response>"""


# ── Language IVR ──────────────────────────────────────────────────────────────
# How each language's menu option is spoken (Twilio <Say> voice + language). This is a
# placeholder voicing for Phase 3a — a later phase swaps in pre-generated audio.
_LANG_LABELS = {
    "en": {"voice": "alice",       "say_lang": "en-US", "press": "For English, press {d}."},
    "ar": {"voice": "Polly.Zeina", "say_lang": "arb",   "press": "للعربية، اضغط {d}."},
    "fr": {"voice": "alice",       "say_lang": "fr-FR", "press": "Pour le français, appuyez sur {d}."},
    "es": {"voice": "alice",       "say_lang": "es-ES", "press": "Para el español, presione {d}."},
}
# Spoken digit per language so "press 2" reads naturally; falls back to the numeral.
_DIGIT_WORDS = {
    "ar": {1: "واحد", 2: "اثنين", 3: "ثلاثة", 4: "أربعة"},
}


def _supported_languages(tenant) -> list[str]:
    """The tenant's supported language codes, normalized (lowercase 2-letter, de-duped,
    order preserved). The FIRST entry is the primary/default language. Always non-empty —
    falls back to ['en'] so a misconfigured tenant still routes (English-safe)."""
    langs: list[str] = []
    for x in (tenant.supported_languages or ["en"]):
        code = str(x).strip().lower()[:2]
        if code and code not in langs:
            langs.append(code)
    return langs or ["en"]


def _digit_to_language(digit: str | None, languages: list[str]) -> str | None:
    """Map a keypress to a language by position (1 -> languages[0], 2 -> languages[1], …).
    Returns None for an empty/non-numeric/out-of-range digit."""
    if not digit or not digit.isdigit():
        return None
    idx = int(digit) - 1
    return languages[idx] if 0 <= idx < len(languages) else None


def _action_url(path: str, **params) -> str:
    """Build a TwiML action/redirect URL with query params, XML-escaping '&' so the URL is
    safe to embed in TwiML attributes/text."""
    if not params:
        return path
    qs = "&amp;".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
    return f"{path}?{qs}"


def _menu_say_lines(languages: list[str]) -> str:
    """One <Say> per supported language, each spoken in its own language/voice and telling
    the caller which key to press for it (e.g. 'For English, press 1.')."""
    lines = []
    for i, lang in enumerate(languages):
        d = i + 1
        label = _LANG_LABELS.get(lang, {"voice": "alice", "say_lang": "en-US",
                                        "press": f"For {lang}, press {{d}}."})
        digit_word = _DIGIT_WORDS.get(lang, {}).get(d, str(d))
        text = label["press"].format(d=digit_word)
        lines.append(f'        <Say voice="{label["voice"]}" language="{label["say_lang"]}">'
                     f'{text}</Say>')
    return "\n".join(lines)


def _language_menu_twiml(languages: list[str], action_url: str) -> str:
    """A <Gather> language menu. The same `action_url` handles both a keypress and (via the
    trailing <Redirect>) a no-input timeout, so /twilio/language-select decides what to do
    on a miss (re-prompt once, then default) — the call is never dropped on silence."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="dtmf" numDigits="1" timeout="6" action="{action_url}" method="POST">
{_menu_say_lines(languages)}
    </Gather>
    <Redirect method="POST">{action_url}</Redirect>
</Response>"""


def _not_configured_twiml() -> str:
    """Spoken to a caller who dialed a number that no tenant owns, then hang up."""
    return ("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you for calling. This number is not yet configured. """
            """Please contact support. Goodbye.</Say>
    <Hangup/>
</Response>""")


@router.post("/inbound")
async def handle_inbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio hits this when someone calls one of our numbers.

    PHONE -> TENANT ROUTING: the dialed number (`To`) identifies the tenant. If a tenant
    owns it, we bridge the call into the LiveKit SIP trunk (the agent loads that tenant's
    config when it joins the room). If NO tenant matches, we play a generic 'not
    configured' message and hang up — the call never reaches an agent."""
    from app.services.tenant_service import resolve_tenant_by_number

    form = await request.form()
    called = form.get("To") or settings.TWILIO_PHONE_NUMBER

    tenant = await resolve_tenant_by_number(db, called)
    if not tenant:
        print(f"[WEBHOOK] inbound To={called!r} -> NO TENANT MATCH "
              "— playing 'not configured' and hanging up", flush=True)
        return Response(content=_not_configured_twiml(), media_type="application/xml")

    # Use the tenant's own number as the SIP user part so the agent resolves the same
    # tenant from the SIP join (consistent with how `To` matched it here).
    sip_number = tenant.twilio_phone_number or called
    niche = tenant.niche.value if tenant.niche else "clinic"
    languages = _supported_languages(tenant)

    # SINGLE-LANGUAGE TENANT: no menu — don't make an English-only caller press anything.
    # Bridge straight to SIP exactly like the current direct path (the language header is
    # this tenant's only language; the agent defaults to it anyway).
    if len(languages) <= 1:
        lang = languages[0]
        sip_uri = f"sip:{sip_number}@{_livekit_sip_host()};transport=tcp"
        print(f"[WEBHOOK] inbound To={called!r} -> tenant {tenant.id} "
              f"({tenant.business_name}) niche={niche} single-language={lang} "
              f"— skipping IVR; bridging to {sip_uri}", flush=True)
        return Response(content=_sip_dial_twiml(sip_number, lang),
                        media_type="application/xml")

    # MULTI-LANGUAGE TENANT: play the keypress menu; the chosen digit is handled by
    # /twilio/language-select, which then dials SIP with the selected language attached.
    print(f"[WEBHOOK] inbound To={called!r} -> tenant {tenant.id} "
          f"({tenant.business_name}) niche={niche} languages={languages} "
          "— playing language selection menu", flush=True)
    action = _action_url("/twilio/language-select", to=called)
    return Response(content=_language_menu_twiml(languages, action),
                    media_type="application/xml")


@router.post("/language-select")
async def handle_language_select(request: Request, db: AsyncSession = Depends(get_db)):
    """Gather action for the language IVR. Receives the keypress (`Digits`), maps it to a
    language by position in the tenant's supported_languages, and dials the LiveKit SIP
    trunk with that language attached (same room/dispatch as the direct path).

    Robust to a missed/invalid keypress: re-prompts ONCE, then defaults to the tenant's
    primary language (the first supported language — `en` for current tenants). It NEVER
    hangs up on silence. `to` (the dialed number) and `reprompt` come via query params so
    the tenant + re-prompt state survive Twilio's <Redirect> on a no-input timeout."""
    from app.services.tenant_service import resolve_tenant_by_number

    form = await request.form()
    digit = (form.get("Digits") or "").strip()
    called = request.query_params.get("to") or form.get("To") or settings.TWILIO_PHONE_NUMBER
    reprompted = request.query_params.get("reprompt") == "1"

    tenant = await resolve_tenant_by_number(db, called)
    if not tenant:
        print(f"[WEBHOOK] language-select To={called!r} -> NO TENANT MATCH "
              "— playing 'not configured' and hanging up", flush=True)
        return Response(content=_not_configured_twiml(), media_type="application/xml")

    languages = _supported_languages(tenant)
    sip_number = tenant.twilio_phone_number or called
    lang = _digit_to_language(digit, languages)

    if lang:
        print(f"[WEBHOOK] language-select To={called!r} digit={digit!r} -> language={lang} "
              f"(tenant {tenant.id}); bridging to SIP", flush=True)
        return Response(content=_sip_dial_twiml(sip_number, lang),
                        media_type="application/xml")

    # Miss (no digit / non-numeric / out of range). Re-prompt exactly once, then default.
    if not reprompted:
        print(f"[WEBHOOK] language-select To={called!r} digit={digit!r} empty/invalid "
              "— re-prompting once", flush=True)
        action = _action_url("/twilio/language-select", to=called, reprompt=1)
        return Response(content=_language_menu_twiml(languages, action),
                        media_type="application/xml")

    primary = languages[0]
    print(f"[WEBHOOK] language-select To={called!r} no valid input after re-prompt "
          f"— defaulting to primary language {primary} (tenant {tenant.id}); bridging to SIP",
          flush=True)
    return Response(content=_sip_dial_twiml(sip_number, primary),
                    media_type="application/xml")


def _hangup_twiml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Hangup/>\n</Response>'


@router.post("/outbound")
async def handle_outbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Called by Twilio when our outbound reminder call is answered.

    With machine detection enabled, Twilio includes `AnsweredBy` here. If it answered to
    a machine (voicemail), we record the outcome and hang up — no point running the agent
    against an answering machine. A human answer is bridged into the LiveKit SIP trunk
    (same path as inbound), where the agent worker joins and runs the reminder script."""
    form = await request.form()
    call_sid = form.get("CallSid")
    answered_by = form.get("AnsweredBy")  # human / machine_start / machine_end_beep / fax / unknown

    if answered_by and (answered_by.startswith("machine") or answered_by == "fax"):
        try:
            from app.services.reminder_service import record_reminder_result_by_sid
            await record_reminder_result_by_sid(call_sid, answered_by=answered_by)
        except Exception as e:
            print(f"[twilio] voicemail record error: {type(e).__name__}: {e}")
        print(f"[twilio] outbound call {call_sid} answered by {answered_by} — hanging up")
        return Response(content=_hangup_twiml(), media_type="application/xml")

    return Response(content=_sip_dial_twiml(), media_type="application/xml")

@router.post("/status")
async def call_status_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio calls this when call status changes (completed, failed, etc)"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration", 0)
    answered_by = form_data.get("AnsweredBy")  # present on AMD status callbacks

    # For outbound reminder calls, map no-answer / busy / failed / voicemail onto the
    # appointment's reminder_outcome (without overriding a human result the agent set).
    try:
        from app.services.reminder_service import record_reminder_result_by_sid
        await record_reminder_result_by_sid(call_sid, twilio_status=call_status,
                                            answered_by=answered_by)
    except Exception as e:
        print(f"[twilio] reminder status record error: {type(e).__name__}: {e}")

    result = await db.execute(select(Call).where(Call.twilio_call_sid == call_sid))
    call = result.scalars().first()

    if call:
        try:
            call.duration_seconds = int(duration)
        except (TypeError, ValueError):
            pass
        call.ended_at = datetime.utcnow()
        # Don't clobber a terminal outcome already recorded (e.g. voicemail/no_answer
        # from AMD, or the agent's resolution) with a generic status mapping.
        if call.outcome == CallOutcome.in_progress:
            if call_status == "completed":
                call.outcome = CallOutcome.resolved
            elif call_status in ["no-answer", "busy"]:
                call.outcome = CallOutcome.no_answer
            elif call_status == "failed":
                call.outcome = CallOutcome.abandoned
        await db.commit()

    return Response(content="OK", media_type="text/plain")

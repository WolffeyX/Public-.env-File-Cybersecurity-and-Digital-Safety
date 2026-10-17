"""Main entry point: one event in, messages and tasks out (Owner C). SDD 5.6, SRS 2.2.

handle_event() is called by the worker (and by tests and scripts/chat_sim.py).
It never calls the network: it reads/writes the Store and returns
Outbound messages and Task jobs for the worker to send/schedule.

Build order (Owner C card):
  M1  route_text: language, DAFTAR, address name, pairing code, help, BAHASA, BERHENTI
      route_button: lang, consent, accept2, stop
  M2  on_image -> question + Task("decode")       (FR-05, FR-08, FR-26)
      on_task "decode" -> save DecodeResult        (uses deps.decode_image)
      on_claim -> verdict.decide() -> verdict text (FR-09..FR-12, FR-15, FR-17, FR-21)
      on_task "reminder" / "close_check"           (FR-24, FR-25)
      paid button                                  (FR-13)
  M3  escalation.start_alert / on_ack / on_escalate (FR-18..FR-20, FR-27)
      reports.open / reports.submit                 (FR-14..FR-16)
"""

from __future__ import annotations

import re
import secrets

from core import escalation, reports
from core import verdict as verdict_rules
from core.messages import DEFAULT_LANG, LANGS, label, render
from core.types import (AlertType, Button, Check, CheckStatus, Claim,
                        DecodeResult, Deps, InboundEvent, Level, Link,
                        Outbound, PairCode, QrKind, ReportReason, Role, Store,
                        Task, User, Verdict)

REMINDER_AFTER_S = 120          # FR-24
CLOSE_AFTER_S = 600             # FR-24
CHECK_TTL_S = 15 * 60           # DR-02
PAIR_TTL_S = 24 * 3600          # DR-05
RATE_LIMIT = 10                 # NFR-SE-05: checks per 10 minutes
RATE_WINDOW_S = 600
SEVERAL = 3                     # distinct scam reports for the "several" wording (FR-15)
COMMANDS = {
    "daftar": "register", "tambah": "add_second",
    "bahasa": "language", "language": "language",
    "berhenti": "stop", "bantuan": "help", "help": "help",
}

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I (NFR-SE-06)
CODE_RE = re.compile(r"^[A-Za-z2-9]{6}$")

# Short note added to a verdict when the image was not a normal payment QR (FR-12).
NOTE_FOR_KIND = {
    QrKind.NO_QR: "e.no_qr",
    QrKind.UNREADABLE: "e.unreadable",
    QrKind.URL: "e.url",
    QrKind.OTHER_TEXT: "e.unknown_scheme",
    QrKind.PAYMENT_OTHER_EMV: "e.unknown_scheme",
}


# ---------------------------------------------------------------------------
# Helpers (M1 step 1). Every later function in this file uses these.
# ---------------------------------------------------------------------------

def get_or_create_user(user_id: str, store: Store, deps: Deps) -> User:
    """Load the user's profile, or create and save a blank one (role NONE)."""
    user = store.get_user(user_id)
    if user is None:
        user = User(user_id=user_id, created_at=deps.now())
        store.put_user(user)
    return user


def lang_of(user: User) -> str:
    """The user's language. Falls back to BM if the value is unknown (FR-04)."""
    return user.lang if user.lang in LANGS else DEFAULT_LANG


def addr(user: User) -> str:
    """How to address the parent: "Mak", "Ayah"... or the default word (NFR-UI-05)."""
    return user.address_as or render("s.default_address", lang_of(user))


def btn(button_id: str, label_id: str, lang: str) -> Button:
    """One button. The id follows "<action>:<value>:<ref>" (types.py)."""
    return Button(id=button_id, label=label(label_id, lang))


def send(to: str, msg_id: str, lang: str,
         buttons: list[Button] | None = None, **params) -> Outbound:
    """Build one message from the catalogue. Code never writes sentences itself (SDD 6.4)."""
    return Outbound(to=to, text=render(msg_id, lang, **params), buttons=buttons or [])


def lang_of_id(user_id: str, store: Store) -> str:
    """Language of someone who may not be loaded yet (used when messaging a contact)."""
    other = store.get_user(user_id)
    return lang_of(other) if other else DEFAULT_LANG


# ---------------------------------------------------------------------------
# M1 step 2: first contact and language choice
# ---------------------------------------------------------------------------

def first_contact(user_id: str) -> list[Outbound | Task]:
    """Greeting for someone we have never seen: language buttons, then welcome (FR-04).
    Uses BM, because nobody has chosen a language yet."""
    lang = DEFAULT_LANG
    return [
        send(user_id, "s.choose_lang", lang,
             [btn("lang:ms:-", "btn.lang_ms", lang),
              btn("lang:en:-", "btn.lang_en", lang)]),
        send(user_id, "s.welcome", lang),
    ]


def on_lang(user: User, value: str, store: Store) -> list[Outbound | Task]:
    """User tapped a language button. Save it and confirm in the new language."""
    if value not in LANGS:
        return []
    user.lang = value
    user.lang_chosen = True
    store.put_user(user)
    return [send(user.user_id, "s.lang_changed", value)]


# ---------------------------------------------------------------------------
# M1 step 3: text commands, parent's name, pairing code
# ---------------------------------------------------------------------------

def lang_buttons(lang: str) -> list[Button]:
    return [btn("lang:ms:-", "btn.lang_ms", lang),
            btn("lang:en:-", "btn.lang_en", lang)]


def new_pair_code(store: Store, now: float) -> str:
    """6 random characters. Retries in the (very unlikely) case the code is taken."""
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if store.peek_pair_code(code, now) is None:
            return code


def on_register(user: User, store: Store) -> list[Outbound | Task]:
    """DAFTAR: this user becomes a primary contact (FR-01). Ask what to call the parent."""
    lang = lang_of(user)
    if user.role != Role.NONE:                 # already registered: just show help
        return [send(user.user_id, "h.help", lang)]
    user.role = Role.PRIMARY
    store.put_user(user)
    return [send(user.user_id, "s.ask_address", lang)]


def on_address_answer(user: User, text: str, store: Store, deps: Deps):
    """The primary contact told us what to call the parent. Save it, issue a code (FR-01)."""
    lang = lang_of(user)
    words = text.split()
    if not words:
        return [send(user.user_id, "s.ask_address", lang)]
    name = words[0][:20]
    name = name[0].upper() + name[1:]          # "mak" -> "Mak"
    user.address_as = name
    store.put_user(user)
    now = deps.now()
    code = new_pair_code(store, now)
    store.put_pair_code(PairCode(
        code=code, owner_id=user.user_id, target_role=Role.PARENT,
        address_as=name, expires_at=now + PAIR_TTL_S))
    return [send(user.user_id, "s.pair_code", lang, code=code, address_as=name)]


def on_code(user: User, text: str, store: Store, deps: Deps):
    """Someone sent something that looks like a pairing code (FR-02, FR-03)."""
    lang = lang_of(user)
    code = text.upper()
    pc = store.peek_pair_code(code, deps.now())   # peek: look, but do not use it up yet
    if pc is None or pc.owner_id == user.user_id:
        return [send(user.user_id, "s.code_invalid", lang)]
    name = pc.address_as or render("s.default_address", lang)
    if pc.target_role == Role.PARENT:
        return [send(user.user_id, "s.consent", lang,
                     [btn(f"consent:yes:{code}", "btn.agree", lang)],
                     address_as=name)]
    if pc.target_role == Role.SECOND:
        return [send(user.user_id, "s.second_invite", lang,
                     [btn(f"accept2:yes:{code}", "btn.accept", lang)],
                     address_as=name)]
    return [send(user.user_id, "s.code_invalid", lang)]


# ---------------------------------------------------------------------------
# M1 step 4: consent, stop, second contact
# ---------------------------------------------------------------------------

def on_consent(user: User, code: str, store: Store, deps: Deps):
    """Parent tapped "Setuju": link to the primary contact (FR-02, FR-21)."""
    lang = lang_of(user)
    now = deps.now()
    pc = store.peek_pair_code(code, now)
    if (pc is None or pc.target_role != Role.PARENT or pc.owner_id == user.user_id
            or user.role in (Role.PRIMARY, Role.SECOND)):
        return [send(user.user_id, "s.code_invalid", lang)]
    if store.consume_pair_code(code, now) is None:         # lost a race: code already used
        return [send(user.user_id, "s.code_invalid", lang)]

    name = pc.address_as or render("s.default_address", lang)
    user.role = Role.PARENT
    user.address_as = name
    user.consent_at = now                                   # proof of consent
    user.practice_pending = True                            # next image is a practice check
    store.put_user(user)
    store.put_link(Link(parent_id=user.user_id, contact_id=pc.owner_id,
                        contact_type=Role.PRIMARY, consent_at=now))
    return [
        send(user.user_id, "s.linked_parent", lang, address_as=name),
        send(pc.owner_id, "s.linked_child", lang_of_id(pc.owner_id, store), address_as=name),
        send(user.user_id, "s.practice_invite", lang),
    ]


def on_stop_confirm(user: User, store: Store):
    """BERHENTI confirmed: delete the user and every link (FR-22)."""
    lang = lang_of(user)                       # read it BEFORE we delete the profile
    uid = user.user_id
    others = store.delete_user_everything(uid)
    out: list[Outbound | Task] = [send(uid, "h.stopped", lang)]
    for other_id in others:
        out.append(send(other_id, "h.contact_left", lang_of_id(other_id, store)))
    return out


def on_add_second(user: User, store: Store, deps: Deps):
    """TAMBAH: a linked primary contact asks for a code for a second contact (FR-03)."""
    lang = lang_of(user)
    parent_id = store.find_parent_of(user.user_id) if user.role == Role.PRIMARY else None
    if parent_id is None:
        return [send(user.user_id, "s.not_primary", lang)]
    parent = store.get_user(parent_id)
    name = addr(parent) if parent else render("s.default_address", lang)
    if any(l.contact_type == Role.SECOND for l in store.get_links(parent_id)):
        return [send(user.user_id, "s.second_exists", lang, address_as=name)]
    now = deps.now()
    code = new_pair_code(store, now)
    store.put_pair_code(PairCode(
        code=code, owner_id=user.user_id, target_role=Role.SECOND,
        address_as=name, expires_at=now + PAIR_TTL_S, parent_id=parent_id))
    return [send(user.user_id, "s.second_code", lang, code=code)]


def on_accept2(user: User, code: str, store: Store, deps: Deps):
    """Second contact tapped "Terima" (FR-03)."""
    lang = lang_of(user)
    now = deps.now()
    pc = store.peek_pair_code(code, now)
    if (pc is None or pc.target_role != Role.SECOND or pc.parent_id is None
            or pc.owner_id == user.user_id or user.role != Role.NONE):
        return [send(user.user_id, "s.code_invalid", lang)]
    name = pc.address_as or render("s.default_address", lang)
    if any(l.contact_type == Role.SECOND for l in store.get_links(pc.parent_id)):
        return [send(user.user_id, "s.second_exists", lang, address_as=name)]
    if store.consume_pair_code(code, now) is None:
        return [send(user.user_id, "s.code_invalid", lang)]

    user.role = Role.SECOND
    store.put_user(user)
    store.put_link(Link(parent_id=pc.parent_id, contact_id=user.user_id,
                        contact_type=Role.SECOND, consent_at=now))
    return [
        send(user.user_id, "s.second_linked", lang, address_as=name),
        send(pc.owner_id, "s.second_linked_primary", lang_of_id(pc.owner_id, store),
             address_as=name),
    ]


# ---------------------------------------------------------------------------
# M2 steps 5, 6, 8: image in, question out, decode in the background
# ---------------------------------------------------------------------------

def claim_buttons(check_id: str, lang: str) -> list[Button]:
    """The three "Who asked you to pay?" buttons (FR-08, D-14)."""
    return [
        btn(f"claim:OFFICIAL:{check_id}", "btn.claim_official", lang),
        btn(f"claim:COURIER:{check_id}", "btn.claim_courier", lang),
        btn(f"claim:KNOWN_PERSON:{check_id}", "btn.claim_known", lang),
    ]


def on_image(event, store, deps):
    """A QR image arrived. Ask the question NOW, decode in the background (FR-05, FR-08)."""
    user = get_or_create_user(event.user_id, store, deps)
    lang = lang_of(user)
    now = deps.now()

    # Abuse limit: at most 10 checks per 10 minutes (NFR-SE-05).
    if store.count_recent_checks(user.user_id, now - RATE_WINDOW_S) >= RATE_LIMIT:
        return [send(user.user_id, "h.rate_limited", lang)]

    # A new image replaces any open check (FR-26).
    old = store.get_open_check(user.user_id, now)
    if old is not None:
        old.status = CheckStatus.CLOSED
        store.put_check(old)

    check = Check(
        check_id=deps.new_id(), parent_id=user.user_id, status=CheckStatus.DECODING,
        created_at=now, expires_at=now + CHECK_TTL_S, media_ref=event.media_ref,
        is_practice=user.practice_pending)
    store.put_check(check)
    if user.practice_pending:                  # the practice check is used up (FR-21)
        user.practice_pending = False
        store.put_user(user)

    return [
        send(user.user_id, "q.who_asked", lang, claim_buttons(check.check_id, lang),
             address_as=addr(user)),
        Task("decode", user.user_id, check.check_id, 0),
        Task("reminder", user.user_id, check.check_id, REMINDER_AFTER_S),
        Task("close_check", user.user_id, check.check_id, CLOSE_AFTER_S),
    ]


def on_decode(event, store, deps):
    """Background job: fetch the image, decode it, save the result, forget the image (DR-01)."""
    now = deps.now()
    check = store.get_check(event.user_id, event.ref, now)
    if check is None or check.status != CheckStatus.DECODING:
        return []
    try:
        data = deps.fetch_media(event.user_id, check.media_ref)
        check.decode = deps.decode_image(data)
    except Exception:                          # never show technical errors to a senior (FR-12)
        check.decode = DecodeResult(kind=QrKind.UNREADABLE)
    check.status = CheckStatus.DECODED
    check.media_ref = None                     # DR-01: no image, not even a pointer to it
    store.put_check(check)
    return []


def on_reminder(event, store, deps):
    """2 minutes and still no tap: one reminder that leads with "don't pay" (FR-24)."""
    now = deps.now()
    check = store.get_check(event.user_id, event.ref, now)
    user = store.get_user(event.user_id)
    if check is None or user is None or check.reminded:
        return []
    if check.status not in (CheckStatus.DECODING, CheckStatus.DECODED):
        return []                              # already answered or closed
    check.reminded = True
    store.put_check(check)
    lang = lang_of(user)
    return [send(user.user_id, "q.reminder", lang, claim_buttons(check.check_id, lang))]


def on_close_check(event, store, deps):
    """10 minutes and still no verdict: close the check (FR-24)."""
    check = store.get_check(event.user_id, event.ref, deps.now())
    if check is not None and check.status != CheckStatus.ANSWERED:
        check.status = CheckStatus.CLOSED
        store.put_check(check)
    return []


# ---------------------------------------------------------------------------
# M2 step 7 and 9: the verdict, and "I already paid"
# ---------------------------------------------------------------------------

def _temporary_decide(claim: Claim, decode: DecodeResult | None) -> Verdict:
    """Stand-in for Owner A's verdict.decide(), following SRS 2.2.3 rules V-1..V-5.
    Used ONLY while verdict.decide() still raises NotImplementedError."""
    is_duitnow = decode is not None and decode.kind == QrKind.PAYMENT_DUITNOW
    if claim == Claim.OFFICIAL:                                         # V-1
        return Verdict(Level.STOP, "V-1", "v.stop.official", notify_child=True)
    if claim == Claim.COURIER:
        if is_duitnow and decode.is_personal is True:                   # V-2
            return Verdict(Level.STOP, "V-2", "v.stop.courier_personal", notify_child=True)
        if not is_duitnow:                                              # V-3
            return Verdict(Level.VERIFY, "V-3", "v.verify.courier_unreadable")
        return Verdict(Level.VERIFY, "V-4", "v.verify.courier")         # V-4
    return Verdict(Level.VERIFY, "V-5", "v.verify.known_person")        # V-5


def decide_verdict(claim: Claim, decode: DecodeResult | None) -> Verdict:
    """Use Owner A's rules when they exist, otherwise the temporary ones."""
    try:
        return verdict_rules.decide(claim, decode)
    except NotImplementedError:
        return _temporary_decide(claim, decode)


def evidence_id(n: int) -> str:
    """0 reports -> ev.none, 1-2 -> ev.few, 3 or more -> ev.many (FR-15)."""
    try:
        return verdict_rules.evidence_message_id(n)
    except NotImplementedError:
        return "ev.none" if n == 0 else ("ev.few" if n < SEVERAL else "ev.many")


def on_claim(user: User, value: str, check_id: str, store: Store, deps: Deps):
    """The parent tapped who asked them to pay. Build ONE verdict message (FR-09..FR-12)."""
    lang = lang_of(user)
    now = deps.now()
    check = store.get_check(user.user_id, check_id, now)
    if (check is None or check.status in (CheckStatus.CLOSED, CheckStatus.ANSWERED)
            or check.expires_at <= now):
        return [send(user.user_id, "q.expired", lang)]                   # FR-25
    try:
        claim = Claim(value)
    except ValueError:
        return []

    decode = check.decode                       # None if the decode has not finished
    kind = decode.kind if decode else QrKind.UNREADABLE
    v = decide_verdict(claim, decode)
    name = decode.payee_name if decode and decode.payee_name else render("v.unknown_name", lang)
    a = addr(user)

    lines: list[str] = []
    if check.is_practice:
        lines.append(render("v.practice_prefix", lang))
    lines.append(render(v.message_id, lang, payee_name=name, address_as=a))
    if decode and decode.amount:
        lines.append(render("v.amount", lang, amount=decode.amount))
    note = NOTE_FOR_KIND.get(kind)
    if note:
        lines.append(render(note, lang))
    if decode and decode.report_key:            # reports only add a line, never change the level
        n = store.count_scam_reports(decode.report_key)
        lines.append(render(evidence_id(n), lang, n=n))
    has_contact = bool(store.get_links(user.user_id))
    alert_now = v.level == Level.STOP and has_contact and not check.is_practice
    if alert_now:
        lines.append(render("v.told_contact", lang, address_as=a))
    if v.level == Level.VERIFY:
        lines.append(render("v.semak_mule", lang))

    check.status = CheckStatus.ANSWERED
    check.claim = claim
    check.verdict_level = v.level
    store.put_check(check)

    out: list[Outbound | Task] = [Outbound(
        to=user.user_id, text="\n".join(lines),
        buttons=[btn(f"paid:yes:{check_id}", "btn.paid", lang),
                 btn(f"report:open:{check_id}", "btn.report", lang)])]
    if alert_now:                               # the parent's message goes out first (FR-19)
        out += escalation.start_alert(check, AlertType.STOP, store, deps)
    return out


def on_paid(user: User, check_id: str, store: Store, deps: Deps):
    """The parent says they already paid: bank, 997, 999, police + alert the family (FR-13)."""
    lang = lang_of(user)
    now = deps.now()
    check = store.get_check(user.user_id, check_id, now)
    if check is None or check.expires_at <= now:
        # The check data is deleted after 15 minutes (DR-02), but the parent says money
        # was sent, so the family must still be told. Use a bare stand-in check.
        check = Check(check_id=check_id, parent_id=user.user_id,
                      status=CheckStatus.ANSWERED, created_at=now, expires_at=now)
    has_primary = any(l.contact_type == Role.PRIMARY for l in store.get_links(user.user_id))
    alerting = has_primary and not check.is_practice

    text = render("p.paid", lang)
    if alerting:                       # only say it when it is true
        text += "\n" + render("v.told_contact", lang, address_as=addr(user))
    out: list[Outbound | Task] = [Outbound(to=user.user_id, text=text)]
    if not check.is_practice:
        out += escalation.start_alert(check, AlertType.PAID, store, deps)
    return out


# ---------------------------------------------------------------------------
# M3: reports
# ---------------------------------------------------------------------------

def on_report(user: User, value: str, check_id: str, store: Store, deps: Deps):
    """"Laporkan QR ini" (value "open"), then the chosen reason (FR-14..FR-16)."""
    lang = lang_of(user)
    now = deps.now()
    check = store.get_check(user.user_id, check_id, now)
    if check is None or check.expires_at <= now:          # the QR details are gone (DR-02)
        return [send(user.user_id, "q.expired", lang)]
    if value == "open":
        return reports.open_report(check, user.user_id, lang)
    try:
        reason = ReportReason(value)
    except ValueError:
        return []
    return reports.submit_report(check, user.user_id, lang, reason, store, deps)


# ---------------------------------------------------------------------------
# Entry point and routers
# ---------------------------------------------------------------------------

def handle_event(event: InboundEvent, store: Store, deps: Deps) -> list[Outbound | Task]:
    """Dispatch one event. Duplicate msg_ids return [] (SDD 10)."""
    if not store.mark_seen(event.msg_id, deps.now()):
        return []
    if event.kind != "task" and store.get_user(event.user_id) is None:
        get_or_create_user(event.user_id, store, deps)     # remember them for next time
        return first_contact(event.user_id)
    if event.kind == "text":
        return route_text(event, store, deps)
    if event.kind == "image":
        return on_image(event, store, deps)
    if event.kind == "button":
        return route_button(event, store, deps)
    if event.kind == "task":
        return route_task(event, store, deps)
    return []


def route_text(event, store, deps):
    user = get_or_create_user(event.user_id, store, deps)
    lang = lang_of(user)
    text = (event.text or "").strip()
    cmd = COMMANDS.get(text.lower())

    if cmd == "register":
        return on_register(user, store)
    if cmd == "add_second":
        return on_add_second(user, store, deps)
    if cmd == "language":
        return [send(user.user_id, "s.choose_lang", lang, lang_buttons(lang))]
    if cmd == "stop":
        return [send(user.user_id, "h.stop_confirm", lang,
                     [btn("stop:confirm:-", "btn.stop_confirm", lang)])]
    if cmd == "help":
        return [send(user.user_id, "h.help", lang)]

    # Not a command. Are we waiting for the parent's name?
    if user.role == Role.PRIMARY and not user.address_as:
        return on_address_answer(user, text, store, deps)

    # Does it look like a pairing code?
    if CODE_RE.match(text):
        return on_code(user, text, store, deps)

    return [send(user.user_id, "h.help", lang)]          # FR-23


def route_button(event, store, deps):
    """Button ids look like "<action>:<value>:<ref>" (types.py)."""
    user = get_or_create_user(event.user_id, store, deps)
    action, value, ref = event.button_id.split(":", 2)
    if action == "lang":
        return on_lang(user, value, store)
    if action == "consent":
        return on_consent(user, ref.upper(), store, deps)
    if action == "accept2":
        return on_accept2(user, ref.upper(), store, deps)
    if action == "stop" and value == "confirm":
        return on_stop_confirm(user, store)
    if action == "claim":
        return on_claim(user, value, ref, store, deps)
    if action == "paid":
        return on_paid(user, ref, store, deps)
    if action == "ack":
        return escalation.on_ack(ref, event.user_id, store, deps)
    if action == "report":
        return on_report(user, value, ref, store, deps)
    return []


def route_task(event, store, deps):
    """Jobs that come back from our own queues (types.py, Task)."""
    if event.task == "decode":
        return on_decode(event, store, deps)
    if event.task == "reminder":
        return on_reminder(event, store, deps)
    if event.task == "close_check":
        return on_close_check(event, store, deps)
    if event.task == "escalate":
        return escalation.on_escalate(event.ref, store, deps)
    return []
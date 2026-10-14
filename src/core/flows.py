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

from core.messages import DEFAULT_LANG, LANGS, label, render
from core.types import (Button, Deps, InboundEvent, Link, Outbound, PairCode,
                        Role, Store, Task, User)

REMINDER_AFTER_S = 120          # FR-24
CLOSE_AFTER_S = 600             # FR-24
CHECK_TTL_S = 15 * 60           # DR-02
PAIR_TTL_S = 24 * 3600          # DR-05
RATE_LIMIT = 10                 # NFR-SE-05: checks per 10 minutes
COMMANDS = {
    "daftar": "register", "tambah": "add_second",
    "bahasa": "language", "language": "language",
    "berhenti": "stop", "bantuan": "help", "help": "help",
}

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I (NFR-SE-06)
CODE_RE = re.compile(r"^[A-Za-z2-9]{6}$")


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
    return []          # claim, paid, report, ack come in Milestones 2 and 3


def on_image(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 2")


def route_task(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 2-3")
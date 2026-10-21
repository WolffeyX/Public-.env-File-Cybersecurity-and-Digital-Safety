"""Extra message rules and worst-case lengths (Owner C).
Kept separate from test_messages.py (Owner A) so the two never conflict."""

import re

import pytest

try:
    from tests.fakes import Clock, InMemoryStore, ev, make_deps
except ImportError:                      # if tests/ is not a package in your repo
    from fakes import Clock, InMemoryStore, ev, make_deps

from core import flows
from core.messages import LANGS, catalogue
from core.types import DecodeResult, Link, QrKind, ReportReason, Role, Task, User

# \b means "penipuan" (fraud) is allowed, but "penipu" (scammer) is not (NFR-LE-02)
NO_ACCUSATION = re.compile(r"\bpenipu\b|\bscammers?\b|\bfraudsters?\b", re.I)
STOP_OPEN = {"ms": "\U0001F6D1 JANGAN BAYAR", "en": "\U0001F6D1 DO NOT PAY"}     # NFR-UI-04
VERIFY_OPEN = {"ms": "\U0001F7E1 Tunggu dulu", "en": "\U0001F7E1 Wait"}
ALERT_OPEN = {"ms": "AMARAN: Telefon {address_as} sekarang.",                    # FR-18
              "en": "ALERT: Call {address_as} now."}
CODE_WORD = {"ms": "kod rahsia", "en": "code word"}                              # NFR-US-06
DISCLAIMER = {"ms": "bukan bank", "en": "not a bank"}                            # NFR-LE-01
STOP_WORD = {"ms": "BERHENTI", "en": "STOP"}                                     # NFR-SE-07


@pytest.mark.parametrize("lang", LANGS)
def test_nobody_is_called_a_scammer(lang):
    for key, text in catalogue(lang).items():
        assert not NO_ACCUSATION.search(text), f"{lang}:{key}"


@pytest.mark.parametrize("lang", LANGS)
def test_verdicts_open_with_symbol_and_instruction(lang):
    for key, text in catalogue(lang).items():
        if key.startswith("v.stop."):
            assert text.startswith(STOP_OPEN[lang]), f"{lang}:{key}"
        if key.startswith("v.verify."):
            assert text.startswith(VERIFY_OPEN[lang]), f"{lang}:{key}"


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", ["a.child.stop", "a.child.paid"])
def test_alerts_open_with_the_call_instruction_and_mention_the_code_word(lang, key):
    text = catalogue(lang)[key]
    assert text.lstrip("\u26a0\ufe0f ").startswith(ALERT_OPEN[lang])
    assert CODE_WORD[lang] in text.lower()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", ["v.verify.known_person", "s.pair_code"])
def test_code_word_is_mentioned_where_the_srs_requires_it(lang, key):
    assert CODE_WORD[lang] in catalogue(lang)[key].lower()


@pytest.mark.parametrize("lang", LANGS)
def test_welcome_disclaimer_and_consent_notice(lang):
    assert DISCLAIMER[lang] in catalogue(lang)["s.welcome"].lower()     # NFR-LE-01
    assert STOP_WORD[lang] in catalogue(lang)["s.consent"]               # NFR-SE-07


# ---- worst case: the REAL combined messages, longest values (NFR-UI-03) ----

LONG_NAME = "N" * 25            # the longest payee name a QR can carry
LONG_ADDRESS = "A" * 20         # the longest name flows.py accepts for "Mak"/"Ayah"
PARENT, CHILD = "wa:601", "wa:602"


def _qr(**kw):
    base = dict(kind=QrKind.PAYMENT_DUITNOW, network_id="A0000006150001",
                crc_ok=True, payee_name=LONG_NAME)
    base.update(kw)
    return DecodeResult(**base)


CASES = {
    "personal_static": _qr(static_dynamic="static", is_personal=True, mcc="0000",
                           report_key="k-long"),
    "business_static": _qr(static_dynamic="static", is_personal=False, mcc="7311",
                           report_key="k-long"),
    "business_dynamic": _qr(static_dynamic="dynamic", is_personal=False, mcc="4722",
                            amount="999999.99"),
    "no_qr": DecodeResult(kind=QrKind.NO_QR),
    "url": DecodeResult(kind=QrKind.URL),
    "unreadable": DecodeResult(kind=QrKind.UNREADABLE),
    "other_text": DecodeResult(kind=QrKind.OTHER_TEXT),
    "other_emv": DecodeResult(kind=QrKind.PAYMENT_OTHER_EMV),
}


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("practice", [False, True])
@pytest.mark.parametrize("claim", ["OFFICIAL", "COURIER", "KNOWN_PERSON"])
@pytest.mark.parametrize("case", sorted(CASES))
def test_real_messages_fit_450_characters_and_8_lines(case, claim, practice, lang):
    clock = Clock()
    store = InMemoryStore()
    media = f"x_{case}"
    deps = make_deps(clock, {media: CASES[case]})
    store.put_user(User(PARENT, role=Role.PARENT, lang=lang, address_as=LONG_ADDRESS,
                        practice_pending=practice))
    store.put_user(User(CHILD, role=Role.PRIMARY, lang=lang))
    store.put_link(Link(PARENT, CHILD, Role.PRIMARY, 1.0))
    for i in range(2):                      # two scam reports -> the longest evidence line
        store.add_report("k-long", f"reporter{i}", ReportReason.SCAM_PATTERN, clock())

    out = flows.handle_event(ev(PARENT, "image", clock, media_ref=media), store, deps)
    check_id = out[1].ref
    flows.handle_event(ev(PARENT, "task", clock, task="decode", ref=check_id), store, deps)
    sent = flows.handle_event(
        ev(PARENT, "button", clock, button_id=f"claim:{claim}:{check_id}"), store, deps)
    sent += flows.handle_event(
        ev(PARENT, "button", clock, button_id=f"paid:yes:{check_id}"), store, deps)

    for m in sent:
        if isinstance(m, Task):
            continue
        assert len(m.text) <= 700, (case, claim, practice, lang, len(m.text))
        assert len(m.text.splitlines()) <= 10, (case, claim, practice, lang)
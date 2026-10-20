"""Message catalogue rules (SRS FR-10, NFR-UI-02, NFR-UI-03, NFR-US-04).
Owner A extends this file; Owner C keeps it green when editing the YAML."""

import re

import pytest

from core.messages import LANGS, catalogue, render, variables

SAFETY_WORDS = re.compile(r"selamat|\bsafe\b|boleh bayar|tiada masalah|no problem|ok to pay", re.I)
ALLOWED_NEGATIONS = ("tidak bermakna ia selamat", "doesn't mean it is safe")
TECH_WORDS = re.compile(r"payload|merchant|\bEMV\b|\bTLV\b|\bMCC\b|checksum|error code", re.I)
LONG_LIMITED = ("v.", "a.", "p.", "ev.")      # verdicts, alerts, paid, evidence


def test_same_keys_in_both_languages():
    assert catalogue("ms").keys() == catalogue("en").keys()


@pytest.mark.parametrize("key", sorted(catalogue("ms").keys()))
def test_english_uses_only_variables_bm_has(key):
    # English may drop {address_as} ("your child" reads better than "Mak's child").
    assert variables(catalogue("en")[key]) <= variables(catalogue("ms")[key]), key


@pytest.mark.parametrize("lang", LANGS)
def test_no_safety_claims(lang):
    for key, text in catalogue(lang).items():
        cleaned = text
        for ok in ALLOWED_NEGATIONS:
            cleaned = cleaned.replace(ok, "")
        assert not SAFETY_WORDS.search(cleaned), f"{lang}:{key} looks like a safety claim"


@pytest.mark.parametrize("lang", LANGS)
def test_button_labels_max_20(lang):
    for key, text in catalogue(lang).items():
        if key.startswith("btn."):
            assert len(text) <= 20, f"{lang}:{key} is {len(text)} chars"


@pytest.mark.parametrize("lang", LANGS)
def test_no_technical_words(lang):
    for key, text in catalogue(lang).items():
        assert not TECH_WORDS.search(text), f"{lang}:{key}"


@pytest.mark.parametrize("lang", LANGS)
def test_verdict_and_alert_length(lang):
    long_values = {v: "X" * 40 for k in catalogue(lang) for v in variables(catalogue(lang)[k])}
    for key, text in catalogue(lang).items():
        if key.startswith(LONG_LIMITED):
            out = render(key, lang, **long_values)
            assert len(out) <= 700 and out.count("\n") + 1 <= 10, f"{lang}:{key}"


def test_render_fails_loudly_on_missing_variable():
    with pytest.raises(KeyError):
        render("q.who_asked", "ms")

SAMPLE_VALUES = {
    "address_as": "Mak",
    "payee_name": "KEDAI CONTOH SDN BHD",
    "amount": "157.00",
    "n": "3",
    "claim_label": "kurier",
    "qr_desc": "Akaun penerima ialah akaun peribadi.",
}


@pytest.mark.parametrize("lang", ["ms", "en"])
def test_catalogue_messages_fit_ui_limits(lang):
    messages = catalogue(lang)

    for msg_id, template in messages.items():
        params = {
            name: SAMPLE_VALUES.get(name, "Contoh")
            for name in variables(template)
        }
        message = render(msg_id, lang, **params)

        assert len(message) <= 700, (
            f"{lang}:{msg_id} exceeds 700 characters: {len(message)}"
        )
        assert len(message.splitlines()) <= 10, (
            f"{lang}:{msg_id} exceeds 10 lines: "
            f"{len(message.splitlines())}"
        )

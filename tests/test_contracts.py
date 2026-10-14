"""Checks the shared contracts and the reference InMemoryStore. Keep passing."""

from core.types import Button, DecodeResult, Level, QrKind


def test_level_has_no_safe():
    assert {l.value for l in Level} == {"STOP", "VERIFY"}


def test_decode_result_round_trip():
    d = DecodeResult(kind=QrKind.PAYMENT_DUITNOW, is_personal=True, payee_name="X")
    assert DecodeResult.from_dict(d.to_dict()) == d


def test_button_id_fits_telegram_limit():
    """Telegram callback_data is max 64 bytes; our longest id must fit."""
    longest = Button(id="claim:KNOWN_PERSON:" + "1760000000000abcdef12", label="x")
    assert len(longest.id.encode()) <= 64

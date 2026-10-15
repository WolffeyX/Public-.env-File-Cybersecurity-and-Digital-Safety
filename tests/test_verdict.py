from core.types import Claim, DecodeResult, Level, QrKind
from core.verdict import decide, evidence_message_id

def test_v1_official_always_stops():
    result = decide(Claim.OFFICIAL, None)

    assert result.level == Level.STOP
    assert result.rule == "V-1"
    assert result.message_id == "v.stop.official"
    assert result.notify_child is True

def test_v2_courier_personal_duitnow_stops():
    decode = DecodeResult(
        kind=QrKind.PAYMENT_DUITNOW,
        is_personal=True,
        payee_name="ALI",
        amount="10.00",
    )
    result = decide(Claim.COURIER, decode)

    assert result.level == Level.STOP
    assert result.rule == "V-2"
    assert result.message_id == "v.stop.courier_personal"
    assert result.notify_child is True
    assert result.params == {
        "payee_name": "ALI",
        "amount": "10.00",
    }

def test_v3_courier_non_duitnow_verifies():
    decode = DecodeResult(kind=QrKind.URL)
    result = decide(Claim.COURIER, decode)

    assert result.level == Level.VERIFY
    assert result.rule == "V-3"
    assert result.message_id == "v.verify.courier_unreadable"
    assert result.notify_child is False

def test_v4_courier_business_duitnow_verifies():
    decode = DecodeResult(
        kind=QrKind.PAYMENT_DUITNOW,
        is_personal=False,
    )
    result = decide(Claim.COURIER, decode)

    assert result.level == Level.VERIFY
    assert result.rule == "V-4"
    assert result.message_id == "v.verify.courier"
    assert result.notify_child is False

def test_v5_known_person_verifies():
    decode = DecodeResult(kind=QrKind.PAYMENT_DUITNOW)
    result = decide(Claim.KNOWN_PERSON, decode)

    assert result.level == Level.VERIFY
    assert result.rule == "V-5"
    assert result.message_id == "v.verify.known_person"
    assert result.notify_child is False

def test_evidence_message_id_thresholds():
    assert evidence_message_id(0) == "ev.none"
    assert evidence_message_id(1) == "ev.few"
    assert evidence_message_id(2) == "ev.few"
    assert evidence_message_id(3) == "ev.many"
    assert evidence_message_id(10) == "ev.many"
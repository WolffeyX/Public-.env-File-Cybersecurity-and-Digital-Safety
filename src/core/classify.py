"""QR text -> DecodeResult (Owner A). SDD 3.4, 3.5, SRS FR-06/07."""

from __future__ import annotations

import hashlib
import hmac

from core.types import DecodeResult, QrKind


def classify(payload: str | None, pepper: bytes) -> DecodeResult:
    """Classify decoded QR text without guessing missing fields."""
    from core.emv import DUITNOW_ID, parse_nested, parse_tlv, validate_crc

    if payload is None:
        return DecodeResult(kind=QrKind.NO_QR)

    if payload.startswith(("http://", "https://")):
        return DecodeResult(kind=QrKind.URL)

    fields, error = parse_tlv(payload)

    # Only classify as EMV if the entire payload parses successfully.
    if error is not None or not fields:
        return DecodeResult(kind=QrKind.OTHER_TEXT)

    values = {field.tag: field.value for field in fields}

    # Require a recognised EMV format indicator.
    if values.get("00") not in ("01", "02"):
        return DecodeResult(kind=QrKind.OTHER_TEXT)

    # A valid EMV payload must have a recognised CRC field.
    crc_ok = validate_crc(payload)

    # Locate the DuitNow network identifier in tag 26.
    account_info = parse_nested(values.get("26", ""))
    network_id = account_info.get("00")

    if network_id is None:
        return DecodeResult(kind=QrKind.OTHER_TEXT)

    if network_id != DUITNOW_ID:
        return DecodeResult(
            kind=QrKind.PAYMENT_OTHER_EMV,
            crc_ok=crc_ok,
            network_id=network_id,
        )

    # Tag 01: 11 = static, 12 = dynamic.
    point_of_initiation = values.get("01")
    if point_of_initiation == "11":
        static_dynamic = "static"
    elif point_of_initiation == "12":
        static_dynamic = "dynamic"
    else:
        static_dynamic = "unknown"

    # Tag 52: 0000 = personal; another four-digit MCC = business.
    mcc = values.get("52")
    if mcc == "0000":
        is_personal = True
    elif mcc is not None and len(mcc) == 4 and mcc.isdigit():
        is_personal = False
    else:
        is_personal = None

    # Only static QRs get a report key. Never include sub-field 03 or tag 62.
    report_key = None
    sub01 = account_info.get("01")
    sub02 = account_info.get("02")
    if static_dynamic == "static" and sub01 is not None and sub02 is not None:
        report_key = make_report_key(pepper, network_id, sub01, sub02)

    return DecodeResult(
        kind=QrKind.PAYMENT_DUITNOW,
        static_dynamic=static_dynamic,
        is_personal=is_personal,
        mcc=mcc,
        payee_name=values.get("59"),
        amount=values.get("54"),
        network_id=network_id,
        crc_ok=crc_ok,
        report_key=report_key,
    )

def make_report_key(pepper: bytes, network_id: str, sub01: str, sub02: str) -> str:
    """HMAC-SHA256 hex of "network_id|sub01|sub02" with the secret pepper (DR-03)."""
    msg = f"{network_id}|{sub01}|{sub02}".encode()
    return hmac.new(pepper, msg, hashlib.sha256).hexdigest()


def decode_and_classify(image_bytes: bytes, pepper: bytes) -> DecodeResult:
    """Decode an image and classify its QR text."""
    from core.decode import UnreadableImage, decode_qr

    try:
        payload = decode_qr(image_bytes)
    except UnreadableImage:
        return DecodeResult(kind=QrKind.UNREADABLE)

    return classify(payload, pepper)
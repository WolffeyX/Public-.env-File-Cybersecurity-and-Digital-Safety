"""QR text -> DecodeResult (Owner A, Milestone 2). SDD 3.4, 3.5, SRS FR-06/07."""

from __future__ import annotations

import hashlib
import hmac

from core.types import DecodeResult, QrKind


def classify(payload: str | None, pepper: bytes) -> DecodeResult:
    """Classify decoded QR text.

    None                                  -> NO_QR
    starts with http:// or https://       -> URL
    first field is tag 00 with value "01" or "02" (your samples all have "02"),
    TLV parses, and tag 26 sub 00 == DUITNOW_ID -> PAYMENT_DUITNOW (fill all fields)
    same EMV checks but another network         -> PAYMENT_OTHER_EMV
    anything else                         -> OTHER_TEXT

    For PAYMENT_DUITNOW:
      static_dynamic: tag 01 "11" -> "static", "12" -> "dynamic", else "unknown"
      is_personal:    tag 52 == "0000" -> True, other 4 digits -> False, missing -> None
      report_key:     static only: make_report_key(pepper, network_id, sub01, sub02)
                      dynamic -> None
      Never use sub-field 03 of tag 26 or tag 62 (may identify a person).
    Missing fields stay None. Never guess (FR-07).
    """
    raise NotImplementedError


def make_report_key(pepper: bytes, network_id: str, sub01: str, sub02: str) -> str:
    """HMAC-SHA256 hex of "network_id|sub01|sub02" with the secret pepper (DR-03)."""
    msg = f"{network_id}|{sub01}|{sub02}".encode()
    return hmac.new(pepper, msg, hashlib.sha256).hexdigest()


def decode_and_classify(image_bytes: bytes, pepper: bytes) -> DecodeResult:
    """What the worker calls (Deps.decode_image). Combines decode.py + classify().
    UnreadableImage -> DecodeResult(kind=QrKind.UNREADABLE)."""
    raise NotImplementedError

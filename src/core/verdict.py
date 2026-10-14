"""Verdict rules (Owner A, Milestone 3). SRS 2.2.3, SDD 5.3.

There is no SAFE level. Reports never change the level (FR-09, FR-15).
"""

from __future__ import annotations

from core.types import Claim, DecodeResult, Level, QrKind, Verdict

SEVERAL = 3   # distinct scam-pattern reporters for the "several" wording (FR-15)


def decide(claim: Claim, decode: DecodeResult | None) -> Verdict:
    """Apply rules V-1 .. V-5 (first match wins). `decode` may be None if
    decoding failed completely; treat that like QrKind.UNREADABLE.

    V-1 OFFICIAL, anything                            -> STOP   "v.stop.official"
    V-2 COURIER, PAYMENT_DUITNOW and is_personal True -> STOP   "v.stop.courier_personal"
    V-3 COURIER, kind not PAYMENT_DUITNOW             -> VERIFY "v.verify.courier_unreadable"
    V-4 COURIER, otherwise                            -> VERIFY "v.verify.courier"
    V-5 KNOWN_PERSON, anything                        -> VERIFY "v.verify.known_person"
    params: payee_name, amount (when known). notify_child = (level is STOP).
    """
    raise NotImplementedError


def evidence_message_id(scam_reports: int) -> str:
    """0 -> "ev.none", 1..SEVERAL-1 -> "ev.few", >= SEVERAL -> "ev.many"."""
    raise NotImplementedError

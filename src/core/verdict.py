"""Verdict rules (Owner A). SRS 2.2.3, SDD 5.3.

There is no SAFE level. Reports never change the level (FR-09, FR-15).
"""

from __future__ import annotations

from core.types import Claim, DecodeResult, Level, QrKind, Verdict

SEVERAL = 3   # distinct scam-pattern reporters for the "several" wording (FR-15)


def decide(claim: Claim, decode: DecodeResult | None) -> Verdict:
    if claim == Claim.OFFICIAL:
        level = Level.STOP
        rule = "V-1"
        message_id = "v.stop.official"

    elif claim == Claim.COURIER and (
        decode is not None
        and decode.kind == QrKind.PAYMENT_DUITNOW
        and decode.is_personal is True
    ):
        level = Level.STOP
        rule = "V-2"
        message_id = "v.stop.courier_personal"

    elif claim == Claim.COURIER and (
        decode is None or decode.kind != QrKind.PAYMENT_DUITNOW
    ):
        level = Level.VERIFY
        rule = "V-3"
        message_id = "v.verify.courier_unreadable"

    elif claim == Claim.COURIER:
        level = Level.VERIFY
        rule = "V-4"
        message_id = "v.verify.courier"

    else:
        level = Level.VERIFY
        rule = "V-5"
        message_id = "v.verify.known_person"

    params = {}
    if decode is not None:
        if decode.payee_name is not None:
            params["payee_name"] = decode.payee_name
        if decode.amount is not None:
            params["amount"] = decode.amount

    return Verdict(
        level=level,
        rule=rule,
        message_id=message_id,
        params=params,
        notify_child=(level == Level.STOP),
    )


def evidence_message_id(scam_reports: int) -> str:
    """0 -> "ev.none", 1..SEVERAL-1 -> "ev.few", >= SEVERAL -> "ev.many"."""
    if scam_reports <= 0:
        return "ev.none"
    if scam_reports < SEVERAL:
        return "ev.few"
    return "ev.many"

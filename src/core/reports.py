"""QR reports (Owner C, Milestone 3). SDD 5.5, SRS FR-14..FR-16."""

from __future__ import annotations

import hashlib
import hmac

from core.messages import label, render
from core.types import Button, Check, Deps, Outbound, ReportReason, Store


def reporter_hash(user_id: str, pepper: bytes) -> str:
    """Scrambled reporter id, so phone numbers are not stored in reports."""
    return hmac.new(pepper, user_id.encode(), hashlib.sha256).hexdigest()


def _report_key(check: Check) -> str | None:
    return check.decode.report_key if check.decode is not None else None


def open_report(check: Check, user_id: str, lang: str) -> list[Outbound]:
    """Show r.choose_reason with 3 buttons (report:<reason>:<check_id>).
    If check.decode.report_key is None -> r.not_reportable."""
    if _report_key(check) is None:                           # FR-16: static DuitNow only
        return [Outbound(to=user_id, text=render("r.not_reportable", lang))]
    buttons = [
        Button(f"report:{ReportReason.SCAM_PATTERN.value}:{check.check_id}",
               label("btn.r_scam", lang)),
        Button(f"report:{ReportReason.DISPUTE.value}:{check.check_id}",
               label("btn.r_dispute", lang)),
        Button(f"report:{ReportReason.OTHER.value}:{check.check_id}",
               label("btn.r_other", lang)),
    ]
    return [Outbound(to=user_id, text=render("r.choose_reason", lang), buttons=buttons)]


def submit_report(check: Check, user_id: str, lang: str, reason: ReportReason,
                  store: Store, deps: Deps) -> list[Outbound]:
    """store.add_report(); r.thanks, or r.already_reported if it returns False."""
    key = _report_key(check)
    if key is None:
        return [Outbound(to=user_id, text=render("r.not_reportable", lang))]
    if check.is_practice:                    # a practice run must never add real evidence
        return [Outbound(to=user_id, text=render("r.thanks", lang))]
    added = store.add_report(key, reporter_hash(user_id, deps.pepper), reason, deps.now())
    msg_id = "r.thanks" if added else "r.already_reported"
    return [Outbound(to=user_id, text=render(msg_id, lang))]

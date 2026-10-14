"""QR reports (Owner C, Milestone 3). SDD 5.5, SRS FR-14..FR-16."""

from __future__ import annotations

import hashlib
import hmac

from core.types import Check, Deps, Outbound, ReportReason, Store


def reporter_hash(user_id: str, pepper: bytes) -> str:
    """Scrambled reporter id, so phone numbers are not stored in reports."""
    return hmac.new(pepper, user_id.encode(), hashlib.sha256).hexdigest()


def open_report(check: Check, user_id: str, lang: str) -> list[Outbound]:
    """Show r.choose_reason with 3 buttons (report:<reason>:<check_id>).
    If check.decode.report_key is None -> r.not_reportable."""
    raise NotImplementedError


def submit_report(check: Check, user_id: str, lang: str, reason: ReportReason,
                  store: Store, deps: Deps) -> list[Outbound]:
    """store.add_report(); r.thanks, or r.already_reported if it returns False."""
    raise NotImplementedError

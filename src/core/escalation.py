"""Family alert state machine (Owner C). SDD 5.4, SRS FR-18..FR-20, FR-27.

    PRIMARY_SENT --ack--> ACKED
    PRIMARY_SENT --180 s, second exists--> SECONDARY_SENT --ack--> ACKED
    PRIMARY_SENT --180 s, no second------> UNACKED
    SECONDARY_SENT --180 s---------------> UNACKED
Every move uses store.transition_alert() so a late timer or a double tap does nothing.
"""

from __future__ import annotations

from core.messages import DEFAULT_LANG, LANGS, label, render
from core.types import (Alert, AlertStage, AlertType, Button, Check, Deps,
                        Outbound, QrKind, Role, Store, Task)

ESCALATE_AFTER_S = 180          # FR-20
ALERT_TTL_S = 7 * 24 * 3600     # DR-06


# ---------------------------------------------------------------------------
# Small helpers. This file must not import flows.py (flows imports this file).
# ---------------------------------------------------------------------------

def _lang(store: Store, user_id: str) -> str:
    """Language of the RECIPIENT, because each person gets the alert in their own language."""
    user = store.get_user(user_id)
    return user.lang if user and user.lang in LANGS else DEFAULT_LANG


def _parent_name(store: Store, parent_id: str, lang: str) -> str:
    parent = store.get_user(parent_id)
    if parent and parent.address_as:
        return parent.address_as
    return render("s.default_address", lang)


def _qr_desc_id(check: Check | None) -> str:
    """Which sentence describes the QR in the STOP alert (FR-18)."""
    decode = check.decode if check is not None else None
    if decode is not None and decode.kind == QrKind.PAYMENT_DUITNOW:
        if decode.is_personal is True:
            return "a.qr_personal"
        if decode.is_personal is False:
            return "a.qr_business"
    return "a.qr_unreadable"


def _alert_message(alert: Alert, check: Check | None, to: str, store: Store) -> Outbound:
    """One alert message for one contact, with the "Saya uruskan" button (FR-18)."""
    lang = _lang(store, to)
    name = _parent_name(store, alert.parent_id, lang)
    claim = check.claim if check is not None else None
    claim_label = render(f"c.{claim.value}", lang) if claim else render("c.unknown", lang)
    button = Button(f"ack:handle:{alert.alert_id}", label("btn.ack", lang))
    if alert.type == AlertType.PAID:
        text = render("a.child.paid", lang, address_as=name, claim_label=claim_label)
    else:
        text = render("a.child.stop", lang, address_as=name, claim_label=claim_label,
                      qr_desc=render(_qr_desc_id(check), lang))
    return Outbound(to=to, text=text, buttons=[button])


# ---------------------------------------------------------------------------
# The three entry points
# ---------------------------------------------------------------------------

def start_alert(check: Check, alert_type: AlertType, store: Store, deps: Deps
                ) -> list[Outbound | Task]:
    """Create the Alert, message the primary contact with an [ack] button,
    and return Task("escalate", ..., delay_s=180). [] if the parent has no links."""
    now = deps.now()
    primary = next((l for l in store.get_links(check.parent_id)
                    if l.contact_type == Role.PRIMARY), None)
    if primary is None:
        return []
    alert_id = f"{check.check_id}-{alert_type.value.lower()}"
    if store.get_alert(alert_id, now) is not None:      # same alert twice: do nothing
        return []
    alert = Alert(alert_id=alert_id, parent_id=check.parent_id, check_id=check.check_id,
                  type=alert_type, stage=AlertStage.PRIMARY_SENT, created_at=now,
                  expires_at=now + ALERT_TTL_S, notified=[primary.contact_id])
    store.put_alert(alert)
    return [
        _alert_message(alert, check, primary.contact_id, store),
        Task("escalate", check.parent_id, alert_id, ESCALATE_AFTER_S),
    ]


def on_ack(alert_id: str, contact_id: str, store: Store, deps: Deps) -> list[Outbound | Task]:
    """PRIMARY_SENT or SECONDARY_SENT -> ACKED. Confirm to the tapper (FR-27),
    tell the other notified contact (a.ack_other). Second tap -> confirmation only."""
    now = deps.now()
    alert = store.get_alert(alert_id, now)
    if alert is None or contact_id not in alert.notified:    # only people we alerted
        return []
    out: list[Outbound | Task] = [
        Outbound(to=contact_id, text=render("a.ack_done", _lang(store, contact_id)))]

    moved = False
    for _ in range(2):      # twice: a timer may move the stage between our read and write
        if alert is None or alert.stage not in (AlertStage.PRIMARY_SENT,
                                                AlertStage.SECONDARY_SENT):
            break
        moved = store.transition_alert(alert_id, alert.stage, AlertStage.ACKED,
                                       acked_by=contact_id)
        if moved:
            break
        alert = store.get_alert(alert_id, now)

    if moved and alert is not None:
        for other in alert.notified:
            if other != contact_id:
                lang = _lang(store, other)
                out.append(Outbound(to=other, text=render(
                    "a.ack_other", lang, address_as=_parent_name(store, alert.parent_id, lang))))
    return out


def on_escalate(alert_id: str, store: Store, deps: Deps) -> list[Outbound | Task]:
    """Timer fired. Move one step as in the diagram above, or do nothing if ACKED."""
    now = deps.now()
    alert = store.get_alert(alert_id, now)
    if alert is None:
        return []

    if alert.stage == AlertStage.PRIMARY_SENT:
        second = next((l for l in store.get_links(alert.parent_id)
                       if l.contact_type == Role.SECOND), None)
        if second is None:                                   # nobody else to ask
            return _give_up(alert, AlertStage.PRIMARY_SENT, store)
        if not store.transition_alert(alert_id, AlertStage.PRIMARY_SENT,
                                      AlertStage.SECONDARY_SENT,
                                      notified_add=second.contact_id):
            return []                                        # someone acked just now
        check = store.get_check(alert.parent_id, alert.check_id, now)
        return [
            _alert_message(alert, check, second.contact_id, store),
            Task("escalate", alert.parent_id, alert_id, ESCALATE_AFTER_S),
        ]

    if alert.stage == AlertStage.SECONDARY_SENT:
        return _give_up(alert, AlertStage.SECONDARY_SENT, store)
    return []                                                # ACKED or UNACKED: nothing to do


def _give_up(alert: Alert, from_stage: AlertStage, store: Store) -> list[Outbound | Task]:
    """Nobody answered: tell the parent to call the bank and 997 (FR-20)."""
    if not store.transition_alert(alert.alert_id, from_stage, AlertStage.UNACKED):
        return []
    lang = _lang(store, alert.parent_id)
    name = _parent_name(store, alert.parent_id, lang)
    return [Outbound(to=alert.parent_id, text=render("a.parent.unacked", lang, address_as=name))]

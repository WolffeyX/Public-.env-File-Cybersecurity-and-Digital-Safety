"""Family alert state machine (Owner C, Milestone 3). SDD 5.4, SRS FR-18..FR-20, FR-27.

    PRIMARY_SENT --ack--> ACKED
    PRIMARY_SENT --180 s, second exists--> SECONDARY_SENT --ack--> ACKED
    PRIMARY_SENT --180 s, no second------> UNACKED
    SECONDARY_SENT --180 s---------------> UNACKED
Every move uses store.transition_alert() so a late timer or a double tap does nothing.
"""

from __future__ import annotations

from core.types import AlertType, Check, Deps, Outbound, Store, Task

ESCALATE_AFTER_S = 180


def start_alert(check: Check, alert_type: AlertType, store: Store, deps: Deps
                ) -> list[Outbound | Task]:
    """Create the Alert, message the primary contact with an [ack] button,
    and return Task("escalate", ..., delay_s=180). [] if the parent has no links."""
    raise NotImplementedError


def on_ack(alert_id: str, contact_id: str, store: Store, deps: Deps) -> list[Outbound | Task]:
    """PRIMARY_SENT or SECONDARY_SENT -> ACKED. Confirm to the tapper (FR-27),
    tell the other notified contact (a.ack_other). Second tap -> confirmation only."""
    raise NotImplementedError


def on_escalate(alert_id: str, store: Store, deps: Deps) -> list[Outbound | Task]:
    """Timer fired. Move one step as in the diagram above, or do nothing if ACKED."""
    raise NotImplementedError

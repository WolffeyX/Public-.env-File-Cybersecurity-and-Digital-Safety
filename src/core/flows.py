"""Main entry point: one event in, messages and tasks out (Owner C). SDD 5.6, SRS 2.2.

handle_event() is called by the worker (and by tests and scripts/chat_sim.py).
It never calls the network: it reads/writes the Store and returns
Outbound messages and Task jobs for the worker to send/schedule.

Build order (Owner C card):
  M1  route_text: language, DAFTAR, address name, pairing code, help, BAHASA, BERHENTI
      route_button: lang, consent, accept2, stop
  M2  on_image -> question + Task("decode")       (FR-05, FR-08, FR-26)
      on_task "decode" -> save DecodeResult        (uses deps.decode_image)
      on_claim -> verdict.decide() -> verdict text (FR-09..FR-12, FR-15, FR-17, FR-21)
      on_task "reminder" / "close_check"           (FR-24, FR-25)
      paid button                                  (FR-13)
  M3  escalation.start_alert / on_ack / on_escalate (FR-18..FR-20, FR-27)
      reports.open / reports.submit                 (FR-14..FR-16)
"""

from __future__ import annotations

from core.types import Deps, InboundEvent, Outbound, Store, Task

REMINDER_AFTER_S = 120          # FR-24
CLOSE_AFTER_S = 600             # FR-24
CHECK_TTL_S = 15 * 60           # DR-02
PAIR_TTL_S = 24 * 3600          # DR-05
RATE_LIMIT = 10                 # NFR-SE-05: checks per 10 minutes
COMMANDS = {
    "daftar": "register", "tambah": "add_second",
    "bahasa": "language", "language": "language",
    "berhenti": "stop", "bantuan": "help", "help": "help",
}


def handle_event(event: InboundEvent, store: Store, deps: Deps) -> list[Outbound | Task]:
    """Dispatch one event. Duplicate msg_ids return [] (SDD 10)."""
    if not store.mark_seen(event.msg_id, deps.now()):
        return []
    if event.kind == "text":
        return route_text(event, store, deps)
    if event.kind == "image":
        return on_image(event, store, deps)
    if event.kind == "button":
        return route_button(event, store, deps)
    if event.kind == "task":
        return route_task(event, store, deps)
    return []


def route_text(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 1")


def route_button(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 1-3")


def on_image(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 2")


def route_task(event, store, deps):
    raise NotImplementedError("Owner C, Milestone 2-3")

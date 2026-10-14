"""Shared contracts for Semak Dulu (SDD section 4.2).

THIS FILE IS THE AGREEMENT BETWEEN OWNERS A, B AND C.
Do not change a name or a field here without telling the other two owners,
because their code and tests depend on it.

Rules that every module must follow:
- core/ never calls the network. It receives data and returns data.
- A user is always identified by one string: "<channel>:<raw id>",
  for example "wa:60123456789" or "tg:987654321".
- There is no SAFE verdict. Level has exactly two members.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class Claim(str, Enum):
    """The parent's answer to "Who asked you to pay?" (SRS 1.4, FR-08)."""
    OFFICIAL = "OFFICIAL"          # Bank / Polis / Mahkamah
    COURIER = "COURIER"            # Kurier
    KNOWN_PERSON = "KNOWN_PERSON"  # Saudara / Kawan / Kedai


class Level(str, Enum):
    """Verdict level. There is deliberately NO "SAFE" member (SRS FR-10)."""
    STOP = "STOP"
    VERIFY = "VERIFY"


class Role(str, Enum):
    PARENT = "parent"
    PRIMARY = "primary"
    SECOND = "second"
    NONE = "none"                  # talked to the bot, not linked yet


class QrKind(str, Enum):
    """Result of classifying a decoded image (SRS FR-06)."""
    PAYMENT_DUITNOW = "payment_duitnow"
    PAYMENT_OTHER_EMV = "payment_other_emv"
    URL = "url"
    OTHER_TEXT = "other_text"
    NO_QR = "no_qr"
    UNREADABLE = "unreadable"


class CheckStatus(str, Enum):
    DECODING = "decoding"          # question sent, decode not finished
    DECODED = "decoded"            # decode finished (any QrKind)
    ANSWERED = "answered"          # verdict sent
    CLOSED = "closed"              # expired or replaced (FR-24, FR-26)


class AlertStage(str, Enum):
    """Alert state machine (SDD 5.4, SRS FR-20)."""
    PRIMARY_SENT = "PRIMARY_SENT"
    SECONDARY_SENT = "SECONDARY_SENT"
    ACKED = "ACKED"
    UNACKED = "UNACKED"


class AlertType(str, Enum):
    STOP = "STOP"
    PAID = "PAID"


class ReportReason(str, Enum):
    SCAM_PATTERN = "scam_pattern"  # counts as evidence (FR-15)
    DISPUTE = "dispute"            # stored, does not count
    OTHER = "other"                # stored, does not count


# --------------------------------------------------------------------------
# Events in and messages out
# --------------------------------------------------------------------------

@dataclass
class InboundEvent:
    """One thing that happened, already converted from WhatsApp/Telegram format.

    kind:
      "text"   - user typed text            -> text is set
      "image"  - user sent/forwarded image  -> media_ref is set
      "button" - user tapped a button       -> button_id is set
      "task"   - internal job from our own queues -> task and ref are set
                 task values: "decode", "reminder", "close_check", "escalate"
    """
    channel: str                   # "wa" | "tg" | "sim" (local simulator)
    user_id: str                   # "wa:60123456789"
    msg_id: str                    # used to skip duplicates
    kind: str
    ts: float
    text: str | None = None
    media_ref: str | None = None   # WhatsApp media id or Telegram file_id
    button_id: str | None = None   # see "Button id format" below
    task: str | None = None
    ref: str | None = None         # check_id or alert_id for tasks


@dataclass
class Button:
    id: str                        # "<action>:<value>:<ref>", max 256 chars
    label: str                     # max 20 characters (WhatsApp limit, NFR-UI-02)


@dataclass
class Outbound:
    """A message for the worker to send."""
    to: str                        # user_id, e.g. "wa:60123456789"
    text: str
    buttons: list[Button] = field(default_factory=list)   # max 3


@dataclass
class Task:
    """A job for the worker to schedule.

    delay_s == 0  -> put on the FIFO events queue (runs next, in order)
    delay_s  > 0  -> put on the timers queue (max 900 s)
    It comes back later as an InboundEvent with kind="task".
    """
    task: str                      # "decode" | "reminder" | "close_check" | "escalate"
    user_id: str
    ref: str
    delay_s: int = 0


# Button id format: "<action>:<value>:<ref>"
#   lang:ms:-              lang:en:-
#   consent:yes:<code>     accept2:yes:<code>       (second contact accepts)
#   claim:OFFICIAL:<check_id>   claim:COURIER:<check_id>   claim:KNOWN_PERSON:<check_id>
#   paid:yes:<check_id>
#   report:open:<check_id>      report:<ReportReason value>:<check_id>
#   ack:handle:<alert_id>
#   stop:confirm:-


# --------------------------------------------------------------------------
# QR decoding and verdict (Owner A produces, Owner C consumes)
# --------------------------------------------------------------------------

@dataclass
class DecodeResult:
    kind: QrKind
    static_dynamic: str = "unknown"      # "static" (tag 01=11) | "dynamic" (12) | "unknown"
    is_personal: bool | None = None      # True: MCC 0000, False: real MCC, None: unknown
    mcc: str | None = None               # tag 52
    payee_name: str | None = None        # tag 59
    amount: str | None = None            # tag 54
    network_id: str | None = None        # tag 26 sub 00
    crc_ok: bool | None = None           # never used to soften a verdict
    report_key: str | None = None        # HMAC, static DuitNow QRs only

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["kind"] = self.kind.value
        return d

    @staticmethod
    def from_dict(d: dict) -> "DecodeResult":
        d = dict(d)
        d["kind"] = QrKind(d["kind"])
        return DecodeResult(**d)


@dataclass
class Verdict:
    level: Level
    rule: str                            # "V-1" .. "V-5" (SRS 2.2.3)
    message_id: str                      # key in messages/*.yaml
    params: dict = field(default_factory=dict)
    notify_child: bool = False           # True only when level is STOP


# --------------------------------------------------------------------------
# Stored records (Owner C stores them, everyone reads them)
# --------------------------------------------------------------------------

@dataclass
class User:
    user_id: str
    role: Role = Role.NONE
    lang: str = "ms"                     # "ms" | "en"
    lang_chosen: bool = False
    address_as: str | None = None        # "Mak", "Ayah" (stored on the parent)
    consent_at: float | None = None      # parent only
    practice_pending: bool = False       # next image is the practice check (FR-21)
    created_at: float = 0.0


@dataclass
class Link:
    parent_id: str
    contact_id: str
    contact_type: Role                   # Role.PRIMARY or Role.SECOND
    consent_at: float


@dataclass
class PairCode:
    code: str
    owner_id: str                        # the primary contact who asked for it
    target_role: Role                    # Role.PARENT or Role.SECOND
    address_as: str | None
    expires_at: float
    parent_id: str | None = None         # set for second-contact codes


@dataclass
class Check:
    check_id: str
    parent_id: str
    status: CheckStatus
    created_at: float
    expires_at: float                    # created_at + 15 min (DR-02)
    media_ref: str | None = None
    decode: DecodeResult | None = None
    claim: Claim | None = None
    verdict_level: Level | None = None
    is_practice: bool = False            # FR-21
    reminded: bool = False               # FR-24


@dataclass
class Alert:
    alert_id: str
    parent_id: str
    check_id: str
    type: AlertType
    stage: AlertStage
    created_at: float
    expires_at: float                    # created_at + 7 days (DR-06)
    acked_by: str | None = None
    notified: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Interfaces
# --------------------------------------------------------------------------

class Channel(Protocol):
    """One messaging platform (Owner B). Implemented in channels/*.py."""
    name: str                                            # "wa" | "tg"

    def verify(self, headers: dict, raw_body: bytes, query: dict) -> bool: ...
    def parse(self, raw_body: bytes) -> list[InboundEvent]: ...
    def send(self, msg: Outbound) -> None: ...
    def fetch_media(self, media_ref: str) -> bytes: ...


class Store(Protocol):
    """All reads and writes (Owner C). InMemoryStore in core/store.py is the
    reference implementation, DynamoStore is the production one.
    Every method that says "atomic" must not double-apply if called twice."""

    # users
    def get_user(self, user_id: str) -> User | None: ...
    def put_user(self, user: User) -> None: ...
    def delete_user_everything(self, user_id: str) -> list[str]:
        """Delete profile and all links that include the user (FR-22).
        Returns the ids of the other people who were linked."""
        ...

    # pairing
    def put_pair_code(self, pc: PairCode) -> None: ...
    def consume_pair_code(self, code: str, now: float) -> PairCode | None:
        """Atomic: returns the code once, then it is gone. None if missing/expired."""
        ...
    def peek_pair_code(self, code: str, now: float) -> PairCode | None: ...

    # links
    def put_link(self, link: Link) -> None: ...
    def get_links(self, parent_id: str) -> list[Link]: ...
    def find_parent_of(self, contact_id: str) -> str | None: ...
    def delete_link(self, parent_id: str, contact_type: Role) -> None: ...

    # checks
    def put_check(self, check: Check) -> None: ...
    def get_check(self, parent_id: str, check_id: str, now: float) -> Check | None: ...
    def get_open_check(self, parent_id: str, now: float) -> Check | None: ...

    # alerts
    def put_alert(self, alert: Alert) -> None: ...
    def get_alert(self, alert_id: str, now: float) -> Alert | None: ...
    def transition_alert(self, alert_id: str, from_stage: AlertStage,
                         to_stage: AlertStage, acked_by: str | None = None,
                         notified_add: str | None = None) -> bool:
        """Atomic: only moves if the current stage == from_stage. True if moved."""
        ...

    # reports
    def add_report(self, report_key: str, reporter_hash: str,
                   reason: ReportReason, now: float) -> bool:
        """Atomic: False if this reporter already reported this key (FR-16)."""
        ...
    def count_scam_reports(self, report_key: str) -> int: ...

    # duplicates and rate limit
    def mark_seen(self, msg_id: str, now: float) -> bool:
        """Atomic: True the first time a msg_id is seen, False afterwards."""
        ...
    def count_recent_checks(self, parent_id: str, since: float) -> int: ...


@dataclass
class Deps:
    """Everything core needs from the outside world, passed in so tests can fake it."""
    fetch_media: Callable[[str, str], bytes]            # (user_id, media_ref) -> image bytes
    decode_image: Callable[[bytes], DecodeResult]       # Owner A: decode + classify
    now: Callable[[], float]
    new_id: Callable[[], str]
    pepper: bytes                                        # secret for HMAC keys (SSM)


# Core entry point (implemented by Owner C in core/flows.py):
#   def handle_event(event: InboundEvent, store: Store, deps: Deps) -> list[Outbound | Task]

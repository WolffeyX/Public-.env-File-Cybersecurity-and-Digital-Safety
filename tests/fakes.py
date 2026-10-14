"""Test helpers shared by all owners."""

from __future__ import annotations

import itertools

from channels.fake import FakeChannel
from core.store import InMemoryStore
from core.types import DecodeResult, Deps, InboundEvent, QrKind


class Clock:
    """Fake time you can move forward: clock.advance(180)."""
    def __init__(self, start: float = 1_760_000_000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


PERSONAL = DecodeResult(kind=QrKind.PAYMENT_DUITNOW, static_dynamic="static", is_personal=True,
                        mcc="0000", payee_name="AHMAD BIN ALI", network_id="A0000006150001",
                        crc_ok=True, report_key="k-personal")
BUSINESS = DecodeResult(kind=QrKind.PAYMENT_DUITNOW, static_dynamic="static", is_personal=False,
                        mcc="7311", payee_name="KEDAI CONTOH SDN BHD", network_id="A0000006150001",
                        crc_ok=True, report_key="k-business")
DYNAMIC = DecodeResult(kind=QrKind.PAYMENT_DUITNOW, static_dynamic="dynamic", is_personal=False,
                       mcc="4722", payee_name="KTMB", amount="157.00",
                       network_id="A0000006150001", crc_ok=True, report_key=None)
NO_QR = DecodeResult(kind=QrKind.NO_QR)
URL = DecodeResult(kind=QrKind.URL)


def make_deps(clock: Clock | None = None, decode_map: dict[str, DecodeResult] | None = None) -> Deps:
    """Deps whose decode_image looks up the media bytes in decode_map
    (e.g. b"personal" -> PERSONAL), so flow tests don't need real images."""
    clock = clock or Clock()
    counter = itertools.count(1)
    table = {b"personal": PERSONAL, b"business": BUSINESS, b"dynamic": DYNAMIC,
             b"noqr": NO_QR, b"url": URL}
    table.update({k.encode(): v for k, v in (decode_map or {}).items()})
    return Deps(
        fetch_media=lambda user_id, ref: ref.encode(),          # media_ref IS the key
        decode_image=lambda b: table.get(b, NO_QR),
        now=clock,
        new_id=lambda: f"id{next(counter):06d}",
        pepper=b"test-pepper",
    )


_ids = itertools.count(1)


def ev(user: str, kind: str, clock: Clock, **kw) -> InboundEvent:
    """Build an InboundEvent quickly: ev("wa:601", "text", clock, text="Daftar")."""
    return InboundEvent(channel=user.split(":")[0], user_id=user, msg_id=f"m{next(_ids)}",
                        kind=kind, ts=clock(), **kw)


__all__ = ["Clock", "FakeChannel", "InMemoryStore", "make_deps", "ev",
           "PERSONAL", "BUSINESS", "DYNAMIC", "NO_QR", "URL"]

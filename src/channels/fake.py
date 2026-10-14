"""In-memory channel for tests and scripts/chat_sim.py. COMPLETE."""

from __future__ import annotations

from core.types import Outbound


class FakeChannel:
    name = "sim"

    def __init__(self, media: dict[str, bytes] | None = None) -> None:
        self.sent: list[Outbound] = []
        self.media = media or {}

    def verify(self, headers, raw_body, query):
        return True

    def parse(self, raw_body):
        return []

    def send(self, msg: Outbound) -> None:
        self.sent.append(msg)

    def fetch_media(self, media_ref: str) -> bytes:
        if media_ref in self.media:
            return self.media[media_ref]
        with open(media_ref, "rb") as f:          # simulator: media_ref is a file path
            return f.read()

    def to(self, user_id: str) -> list[Outbound]:
        return [m for m in self.sent if m.to == user_id]

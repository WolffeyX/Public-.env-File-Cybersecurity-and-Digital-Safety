"""WhatsApp Cloud API adapter (Owner B, Milestone 2). SDD 4.1, 6.2.

Everything marked TBV must be checked against Meta's current docs
(developers.facebook.com/docs/whatsapp/cloud-api). Use the Graph API version
shown in your app dashboard.

Webhook (incoming)
  GET  /wa?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
       -> return hub.challenge as plain text if the token matches (handshake)
  POST /wa  JSON body, header x-hub-signature-256: "sha256=<hex>"
       hex = HMAC-SHA256(app_secret, RAW body bytes)        (TBV)
       Messages are under entry[].changes[].value.messages[]:
         type "text"        -> text.body
         type "image"       -> image.id   (media id)
         type "interactive" -> interactive.button_reply.id   (our Button.id)
       value.statuses[] (delivered/read receipts) -> ignore, return no events
       msg["from"] is the sender phone number, msg["id"] is the message id

Sending (outgoing)   POST https://graph.facebook.com/<ver>/<phone_number_id>/messages
  headers: Authorization: Bearer <token>
  text:    {"messaging_product":"whatsapp","to":raw,"type":"text","text":{"body":...}}
  buttons: {"messaging_product":"whatsapp","to":raw,"type":"interactive",
            "interactive":{"type":"button","body":{"text":...},
              "action":{"buttons":[{"type":"reply","reply":{"id":..,"title":..}}]}}}
           max 3 buttons, title max 20 chars (TBV)

Media download (2 steps, TBV)
  GET https://graph.facebook.com/<ver>/<media_id>   -> {"url": ...}
  GET <url> with the same Authorization header      -> image bytes
"""

from __future__ import annotations

import hashlib
import hmac
import json 

import httpx

from channels.base import make_user_id, split_user_id
from core.types import InboundEvent, Outbound


class WhatsAppChannel:
    name = "wa"

    def __init__(self, token: str, phone_number_id: str, app_secret: str,
                 verify_token: str, api_version: str = "v21.0") -> None:
        self.token = token
        self.phone_number_id = phone_number_id
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.api_version = api_version

    def handshake(self, query: dict) -> str | None:
        """GET verification. Return hub.challenge if mode and token match, else None."""
        if not self.verify_token:                       # (a)
            return None
        if query.get("hub.mode") != "subscribe":        # (b)
            return None
        given = query.get("hub.verify_token", "")       # (c)
        if not hmac.compare_digest(given.encode(), self.verify_token.encode()):  # (d)
            return None
        return query.get("hub.challenge")               # (e)

    def verify(self, headers: dict, raw_body: bytes, query: dict) -> bool:
        """Check x-hub-signature-256 with hmac.compare_digest. Headers are lowercase."""
        if not self.app_secret:                                    # (a)
            return False
        header = headers.get("x-hub-signature-256", "")            # (b)
        if not header.startswith("sha256="):                       # (c)
            return False
        expected = hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()  # (d)
        return hmac.compare_digest(header.removeprefix("sha256="), expected)                # (e)

    def parse(self, raw_body: bytes) -> list[InboundEvent]:
        """Webhook JSON -> InboundEvents. user_id = make_user_id("wa", msg["from"])."""
        try:
            data = json.loads(raw_body)                          # (a)
        except ValueError:
            return []
        events: list[InboundEvent] = []
        for entry in data.get("entry", []):                      # (b)
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):     # statuses[] are ignored  (c)
                    ev = self._to_event(msg)
                    if ev is not None:
                        events.append(ev)
        return events

    def _to_event(self, msg: dict) -> InboundEvent | None:
        """One WhatsApp message -> InboundEvent, or None for types we do not handle."""
        common = dict(channel=self.name,                         # (d)
                      user_id=make_user_id("wa", msg["from"]),
                      msg_id=msg["id"],
                      ts=float(msg.get("timestamp", 0)))
        kind = msg.get("type")
        if kind == "text":
            return InboundEvent(kind="text", text=msg["text"]["body"], **common)
        if kind == "image":
            return InboundEvent(kind="image", media_ref=msg["image"]["id"], **common)
        if kind == "interactive":
            reply = msg["interactive"].get("button_reply")
            if reply:
                return InboundEvent(kind="button", button_id=reply["id"], **common)
        return None                                              # (e)

    def send(self, msg: Outbound) -> None:
        """Text if no buttons, interactive button message otherwise. Raise on HTTP error."""
        _, to = split_user_id(msg.to)                                   # (a)
        if msg.buttons:
            payload = {
                "messaging_product": "whatsapp", "to": to, "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": msg.text},
                    "action": {"buttons": [
                        {"type": "reply", "reply": {"id": b.id, "title": b.label[:20]}}   # (b)
                        for b in msg.buttons[:3]
                    ]},
                },
            }
        else:
            payload = {"messaging_product": "whatsapp", "to": to, "type": "text",
                       "text": {"body": msg.text}}
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        r = httpx.post(url, json=payload, headers=self._auth(), timeout=10)      # (c)
        if r.status_code >= 400:
            raise RuntimeError(f"whatsapp send failed: HTTP {r.status_code}")   # (d)

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}                        # (e)

    def fetch_media(self, media_ref: str) -> bytes:
        """Two steps: media id -> short-lived URL -> image bytes. Bytes stay in memory only."""
        meta = httpx.get(f"https://graph.facebook.com/{self.api_version}/{media_ref}",
                         headers=self._auth(), timeout=10)                          # (a)
        if meta.status_code >= 400:
            raise RuntimeError(f"whatsapp media lookup failed: HTTP {meta.status_code}")
        img = httpx.get(meta.json()["url"], headers=self._auth(), timeout=10)       # (b)
        if img.status_code >= 400:
            raise RuntimeError(f"whatsapp media download failed: HTTP {img.status_code}")
        return img.content                                                          # (c)

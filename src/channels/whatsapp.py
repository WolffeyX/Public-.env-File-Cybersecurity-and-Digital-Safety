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
        raise NotImplementedError("Owner B, Milestone 1")

    def verify(self, headers: dict, raw_body: bytes, query: dict) -> bool:
        """Check x-hub-signature-256 with hmac.compare_digest. Headers are lowercase."""
        raise NotImplementedError("Owner B, Milestone 2")

    def parse(self, raw_body: bytes) -> list[InboundEvent]:
        """Webhook JSON -> InboundEvents. user_id = make_user_id("wa", msg["from"])."""
        raise NotImplementedError("Owner B, Milestone 2")

    def send(self, msg: Outbound) -> None:
        """Text if no buttons, interactive button message otherwise. Raise on HTTP error."""
        raise NotImplementedError("Owner B, Milestone 2")

    def fetch_media(self, media_ref: str) -> bytes:
        raise NotImplementedError("Owner B, Milestone 2")

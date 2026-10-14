"""Telegram Bot API adapter (Owner B, Milestone 3, fallback). SDD 6.3.

Set the webhook once:
  https://api.telegram.org/bot<token>/setWebhook?url=<api>/tg&secret_token=<tg_secret>
Incoming: header x-telegram-bot-api-secret-token must equal tg_secret.
  update.message.text          -> text
  update.message.photo[-1].file_id (largest size) -> image
  update.callback_query.data   -> button (also call answerCallbackQuery)
Sending: POST /bot<token>/sendMessage
  {"chat_id": raw, "text": ..., "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": id}], ...]}}
  callback_data max 64 bytes: our Button ids must stay short (TBV)
Media: GET /bot<token>/getFile?file_id=... -> file_path,
       then GET https://api.telegram.org/file/bot<token>/<file_path>
"""

from __future__ import annotations

from core.types import InboundEvent, Outbound


class TelegramChannel:
    name = "tg"

    def __init__(self, token: str, secret: str) -> None:
        self.token = token
        self.secret = secret

    def verify(self, headers: dict, raw_body: bytes, query: dict) -> bool:
        raise NotImplementedError("Owner B, Milestone 3")

    def parse(self, raw_body: bytes) -> list[InboundEvent]:
        raise NotImplementedError

    def send(self, msg: Outbound) -> None:
        raise NotImplementedError

    def fetch_media(self, media_ref: str) -> bytes:
        raise NotImplementedError

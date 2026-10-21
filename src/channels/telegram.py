"""Telegram Bot API adapter (Owner B). SDD 4.1.

Set the webhook once:
  https://api.telegram.org/bot<token>/setWebhook?url=<api>/tg&secret_token=<tg_secret>
Incoming: header x-telegram-bot-api-secret-token must equal tg_secret.
  update.message.text          -> text
  update.message.photo[-1].file_id (largest size) -> image
  update.callback_query.data   -> button (also call answerCallbackQuery)
Sending: POST /bot<token>/sendMessage
  {"chat_id": raw, "text": ..., "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": id}], ...]}}
  callback_data max 64 bytes: our Button ids must stay short
Media: GET /bot<token>/getFile?file_id=... -> file_path,
       then GET https://api.telegram.org/file/bot<token>/<file_path>
"""

from __future__ import annotations

import hmac
import json
import time

import httpx

from channels.base import make_user_id, split_user_id
from core.types import InboundEvent, Outbound


class TelegramChannel:
    name = "tg"

    def __init__(self, token: str, secret: str) -> None:
        self.token = token
        self.secret = secret

    def verify(self, headers: dict, raw_body: bytes, query: dict) -> bool:
        """Header x-telegram-bot-api-secret-token must equal our secret."""
        if not self.secret:                                            # fail closed
            return False
        given = headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(given.encode(), self.secret.encode())

    def parse(self, raw_body: bytes) -> list[InboundEvent]:
        """One Telegram update -> at most one InboundEvent."""
        try:
            update = json.loads(raw_body)
        except ValueError:
            return []
        msg_id = f"tg:{update.get('update_id')}"
        if "message" in update:
            m = update["message"]
            common = dict(channel=self.name, user_id=make_user_id("tg", m["chat"]["id"]),
                          msg_id=msg_id, ts=float(m.get("date", 0)))
            if "text" in m:
                return [InboundEvent(kind="text", text=m["text"], **common)]
            if m.get("photo"):
                largest = m["photo"][-1]                               # (a)
                return [InboundEvent(kind="image", media_ref=largest["file_id"], **common)]
            return []
        if "callback_query" in update:
            cq = update["callback_query"]
            self._answer_callback(cq["id"])                            # (b)
            chat_id = cq.get("message", {}).get("chat", {}).get("id", cq["from"]["id"])
            return [InboundEvent(channel=self.name, user_id=make_user_id("tg", chat_id),
                                 msg_id=msg_id, kind="button", ts=time.time(),
                                 button_id=cq.get("data", ""))]
        return []                                                      # (c)

    def _answer_callback(self, callback_id: str) -> None:
        """Stop the loading spinner on the tapped button. Best effort: never block the event."""
        try:
            httpx.post(self._api("answerCallbackQuery"),
                       json={"callback_query_id": callback_id}, timeout=3)
        except httpx.HTTPError:
            pass

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def send(self, msg: Outbound) -> None:
        """sendMessage; buttons become an inline keyboard, one button per row."""
        _, chat_id = split_user_id(msg.to)
        payload = {"chat_id": chat_id, "text": msg.text}
        if msg.buttons:
            payload["reply_markup"] = {"inline_keyboard": [
                [{"text": b.label, "callback_data": b.id}] for b in msg.buttons   # (a)
            ]}
        r = httpx.post(self._api("sendMessage"), json=payload, timeout=10)
        if r.status_code >= 400:
            raise RuntimeError(f"telegram send failed: HTTP {r.status_code}")      # (b)

    def fetch_media(self, media_ref: str) -> bytes:
        """getFile -> file_path -> download. Bytes stay in memory only."""
        meta = httpx.get(self._api("getFile"), params={"file_id": media_ref}, timeout=10)
        if meta.status_code >= 400:
            raise RuntimeError(f"telegram getFile failed: HTTP {meta.status_code}")
        path = meta.json()["result"]["file_path"]
        img = httpx.get(f"https://api.telegram.org/file/bot{self.token}/{path}", timeout=10)
        if img.status_code >= 400:
            raise RuntimeError(f"telegram download failed: HTTP {img.status_code}")
        return img.content

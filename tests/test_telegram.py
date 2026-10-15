"""Tests for the Telegram adapter (Owner B, fallback channel). No network, no AWS."""

import json

import httpx
import pytest

from channels.telegram import TelegramChannel


def make_channel(secret="rahsia-tg"):
    return TelegramChannel(token="123:ABC", secret=secret)


class FakeApi:
    """Stands in for httpx.post / httpx.get: records calls, answers from a queue or 200."""

    def __init__(self):
        self.calls = []
        self.responses = []

    def _answer(self):
        return self.responses.pop(0) if self.responses else httpx.Response(200, json={"ok": True})

    def post(self, url, json=None, timeout=None):
        self.calls.append({"method": "POST", "url": url, "json": json, "timeout": timeout})
        return self._answer()

    def get(self, url, params=None, timeout=None):
        self.calls.append({"method": "GET", "url": url, "params": params, "timeout": timeout})
        return self._answer()


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(httpx, "post", fake.post)
    monkeypatch.setattr(httpx, "get", fake.get)
    return fake


# ---------------------------------------------------------------- verify

def test_verify_accepts_matching_secret():
    headers = {"x-telegram-bot-api-secret-token": "rahsia-tg"}
    assert make_channel().verify(headers, b"{}", {}) is True


def test_verify_rejects_wrong_secret():
    headers = {"x-telegram-bot-api-secret-token": "salah"}
    assert make_channel().verify(headers, b"{}", {}) is False


def test_verify_rejects_missing_header():
    assert make_channel().verify({}, b"{}", {}) is False


def test_verify_rejects_when_secret_not_configured():
    headers = {"x-telegram-bot-api-secret-token": ""}
    assert make_channel(secret="").verify(headers, b"{}", {}) is False


# ---------------------------------------------------------------- parse
# Shapes follow the Telegram Bot API "Update" object (TBV against current docs).

def update(**body) -> bytes:
    return json.dumps({"update_id": 1001, **body}).encode()


def test_parse_text_message():
    raw = update(message={"message_id": 5, "date": 1760400000,
                          "chat": {"id": 555, "type": "private"}, "from": {"id": 555},
                          "text": "Daftar"})
    [ev] = make_channel().parse(raw)
    assert ev.channel == "tg"
    assert ev.user_id == "tg:555"
    assert ev.msg_id == "tg:1001"
    assert ev.kind == "text"
    assert ev.text == "Daftar"


def test_parse_photo_uses_largest_size():
    raw = update(message={"message_id": 6, "date": 1760400000,
                          "chat": {"id": 555, "type": "private"}, "from": {"id": 555},
                          "photo": [{"file_id": "SMALL", "width": 90},
                                    {"file_id": "MEDIUM", "width": 320},
                                    {"file_id": "LARGE", "width": 1280}]})
    [ev] = make_channel().parse(raw)
    assert ev.kind == "image"
    assert ev.media_ref == "LARGE"


def test_parse_button_tap_and_answers_callback(api):
    raw = update(callback_query={"id": "CQ1", "from": {"id": 555},
                                 "message": {"message_id": 7, "chat": {"id": 555}},
                                 "data": "lang:ms:-"})
    [ev] = make_channel().parse(raw)
    assert ev.kind == "button"
    assert ev.button_id == "lang:ms:-"
    assert ev.user_id == "tg:555"
    [call] = api.calls
    assert call["url"] == "https://api.telegram.org/bot123:ABC/answerCallbackQuery"
    assert call["json"] == {"callback_query_id": "CQ1"}


def test_parse_button_still_works_if_answer_callback_fails(monkeypatch):
    def broken_post(*args, **kwargs):
        raise httpx.ConnectError("no network")
    monkeypatch.setattr(httpx, "post", broken_post)
    raw = update(callback_query={"id": "CQ1", "from": {"id": 555},
                                 "message": {"chat": {"id": 555}}, "data": "lang:en:-"})
    [ev] = make_channel().parse(raw)
    assert ev.button_id == "lang:en:-"


def test_parse_ignores_other_message_types():
    raw = update(message={"message_id": 8, "date": 1, "chat": {"id": 555},
                          "sticker": {"file_id": "S"}})
    assert make_channel().parse(raw) == []


def test_parse_ignores_other_update_types():
    assert make_channel().parse(update(edited_message={"text": "x"})) == []


def test_parse_bad_json_returns_empty_list():
    assert make_channel().parse(b"not json") == []
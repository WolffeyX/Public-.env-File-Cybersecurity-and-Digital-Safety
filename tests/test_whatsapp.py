"""Tests for the WhatsApp adapter (Owner B). No network, no AWS."""
import json
import hashlib
import hmac
import httpx
import pytest

from channels.whatsapp import WhatsAppChannel
from core.types import Button, Outbound


def make_channel(verify_token="rahsia-ujian"):
    return WhatsAppChannel(token="t", phone_number_id="123",
                           app_secret="s", verify_token=verify_token)


def test_handshake_returns_challenge_when_token_matches():
    query = {"hub.mode": "subscribe", "hub.verify_token": "rahsia-ujian",
             "hub.challenge": "1158201444"}
    assert make_channel().handshake(query) == "1158201444"


def test_handshake_rejects_wrong_token():
    query = {"hub.mode": "subscribe", "hub.verify_token": "salah",
             "hub.challenge": "1158201444"}
    assert make_channel().handshake(query) is None


def test_handshake_rejects_wrong_mode():
    query = {"hub.mode": "unsubscribe", "hub.verify_token": "rahsia-ujian",
             "hub.challenge": "1158201444"}
    assert make_channel().handshake(query) is None


def test_handshake_rejects_empty_query():
    assert make_channel().handshake({}) is None


def test_handshake_rejects_when_verify_token_not_configured():
    query = {"hub.mode": "subscribe", "hub.verify_token": "",
             "hub.challenge": "1158201444"}
    assert make_channel(verify_token="").handshake(query) is None

# ---------------------------------------------------------------- verify (HMAC)

BODY = b'{"object":"whatsapp_business_account","entry":[]}'


def sign(body: bytes, secret: str = "s") -> str:
    """Build the header value the way Meta does: sha256=<hex HMAC of raw body>."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_accepts_correct_signature():
    headers = {"x-hub-signature-256": sign(BODY)}
    assert make_channel().verify(headers, BODY, {}) is True


def test_verify_rejects_signature_from_other_secret():
    headers = {"x-hub-signature-256": sign(BODY, secret="bukan-rahsia-kita")}
    assert make_channel().verify(headers, BODY, {}) is False


def test_verify_rejects_tampered_body():
    headers = {"x-hub-signature-256": sign(BODY)}
    tampered = BODY.replace(b"[]", b"[1]")
    assert make_channel().verify(headers, tampered, {}) is False


def test_verify_rejects_missing_header():
    assert make_channel().verify({}, BODY, {}) is False


def test_verify_rejects_header_without_prefix():
    bare_hex = sign(BODY).removeprefix("sha256=")
    assert make_channel().verify({"x-hub-signature-256": bare_hex}, BODY, {}) is False


def test_verify_rejects_when_app_secret_not_configured():
    ch = WhatsAppChannel(token="t", phone_number_id="123", app_secret="", verify_token="v")
    headers = {"x-hub-signature-256": sign(BODY, secret="")}
    assert ch.verify(headers, BODY, {}) is False

# ---------------------------------------------------------------- parse
# Shapes follow Meta's webhook examples (TBV against current docs).

def webhook(*messages, statuses=None) -> bytes:
    """Wrap messages the way Meta does: entry[].changes[].value.messages[]."""
    value = {"messaging_product": "whatsapp",
             "metadata": {"display_phone_number": "15550000000", "phone_number_id": "123"}}
    if messages:
        value["messages"] = list(messages)
    if statuses:
        value["statuses"] = statuses
    body = {"object": "whatsapp_business_account",
            "entry": [{"id": "WABA_ID", "changes": [{"field": "messages", "value": value}]}]}
    return json.dumps(body).encode()


def test_parse_text_message():
    raw = webhook({"from": "60123456789", "id": "wamid.T1", "timestamp": "1760400000",
                   "type": "text", "text": {"body": "Daftar"}})
    [ev] = make_channel().parse(raw)
    assert ev.channel == "wa"
    assert ev.user_id == "wa:60123456789"
    assert ev.msg_id == "wamid.T1"
    assert ev.kind == "text"
    assert ev.text == "Daftar"
    assert ev.ts == 1760400000.0


def test_parse_image_message_keeps_only_media_id():
    raw = webhook({"from": "60123456789", "id": "wamid.I1", "timestamp": "1760400000",
                   "type": "image",
                   "image": {"id": "MEDIA_ID_1", "mime_type": "image/jpeg", "sha256": "x"}})
    [ev] = make_channel().parse(raw)
    assert ev.kind == "image"
    assert ev.media_ref == "MEDIA_ID_1"
    assert ev.text is None


def test_parse_button_reply():
    raw = webhook({"from": "60123456789", "id": "wamid.B1", "timestamp": "1760400000",
                   "type": "interactive",
                   "interactive": {"type": "button_reply",
                                   "button_reply": {"id": "lang:ms:-", "title": "Bahasa Melayu"}}})
    [ev] = make_channel().parse(raw)
    assert ev.kind == "button"
    assert ev.button_id == "lang:ms:-"


def test_parse_ignores_status_updates():
    raw = webhook(statuses=[{"id": "wamid.X", "status": "delivered",
                             "timestamp": "1760400000", "recipient_id": "60123456789"}])
    assert make_channel().parse(raw) == []


def test_parse_ignores_unsupported_types():
    raw = webhook({"from": "60123456789", "id": "wamid.A1", "timestamp": "1760400000",
                   "type": "audio", "audio": {"id": "MEDIA_ID_2"}})
    assert make_channel().parse(raw) == []


def test_parse_handles_several_messages_in_one_webhook():
    raw = webhook(
        {"from": "60111111111", "id": "wamid.1", "timestamp": "1", "type": "text",
         "text": {"body": "hai"}},
        {"from": "60122222222", "id": "wamid.2", "timestamp": "2", "type": "text",
         "text": {"body": "Daftar"}},
    )
    events = make_channel().parse(raw)
    assert [e.user_id for e in events] == ["wa:60111111111", "wa:60122222222"]


def test_parse_bad_json_returns_empty_list():
    assert make_channel().parse(b"not json") == []

# ---------------------------------------------------------------- send

class FakeGraph:
    """Stands in for httpx.post: records each call and answers with `status`."""

    def __init__(self):
        self.calls = []
        self.status = 200
        self.get_responses = []      # queued answers for httpx.get, in order

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return httpx.Response(self.status)

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.get_responses.pop(0)


@pytest.fixture
def graph(monkeypatch):
    """Replace httpx.post so no real request leaves the laptop."""
    fake = FakeGraph()
    monkeypatch.setattr(httpx, "post", fake.post)
    monkeypatch.setattr(httpx, "get", fake.get)
    return fake


def test_send_plain_text(graph):
    make_channel().send(Outbound(to="wa:60123456789", text="Hai!"))
    [call] = graph.calls
    assert call["url"] == "https://graph.facebook.com/v21.0/123/messages"
    assert call["headers"] == {"Authorization": "Bearer t"}
    assert call["timeout"] == 10
    assert call["json"] == {"messaging_product": "whatsapp", "to": "60123456789",
                            "type": "text", "text": {"body": "Hai!"}}


def test_send_buttons_as_interactive_message(graph):
    msg = Outbound(to="wa:60123456789", text="Pilih bahasa",
                   buttons=[Button("lang:ms:-", "Bahasa Melayu"), Button("lang:en:-", "English")])
    make_channel().send(msg)
    body = graph.calls[0]["json"]
    assert body["type"] == "interactive"
    assert body["interactive"]["type"] == "button"
    assert body["interactive"]["body"] == {"text": "Pilih bahasa"}
    assert body["interactive"]["action"]["buttons"] == [
        {"type": "reply", "reply": {"id": "lang:ms:-", "title": "Bahasa Melayu"}},
        {"type": "reply", "reply": {"id": "lang:en:-", "title": "English"}},
    ]


def test_send_raises_on_http_error_without_leaking_details(graph):
    graph.status = 401  # e.g. expired token
    with pytest.raises(RuntimeError) as err:
        make_channel().send(Outbound(to="wa:60123456789", text="rahsia"))
    assert "401" in str(err.value)
    assert "60123456789" not in str(err.value)   # DR-09: no phone number in logs
    assert "rahsia" not in str(err.value)        # no message text in logs

# ---------------------------------------------------------------- fetch_media

def test_fetch_media_two_steps(graph):
    graph.get_responses = [
        httpx.Response(200, json={"url": "https://lookaside.example/abc", "mime_type": "image/jpeg"}),
        httpx.Response(200, content=b"\xff\xd8fake-jpeg"),
    ]
    data = make_channel().fetch_media("MEDIA_ID_1")
    assert data == b"\xff\xd8fake-jpeg"
    first, second = graph.calls
    assert first["url"] == "https://graph.facebook.com/v21.0/MEDIA_ID_1"
    assert second["url"] == "https://lookaside.example/abc"
    assert second["headers"] == {"Authorization": "Bearer t"}   # the download needs the token too


def test_fetch_media_raises_when_lookup_fails(graph):
    graph.get_responses = [httpx.Response(404)]
    with pytest.raises(RuntimeError, match="404"):
        make_channel().fetch_media("MEDIA_ID_1")


def test_fetch_media_raises_when_download_fails(graph):
    graph.get_responses = [
        httpx.Response(200, json={"url": "https://lookaside.example/abc"}),
        httpx.Response(403),
    ]
    with pytest.raises(RuntimeError, match="403"):
        make_channel().fetch_media("MEDIA_ID_1")
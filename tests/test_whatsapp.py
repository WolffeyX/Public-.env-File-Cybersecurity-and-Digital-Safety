"""Tests for the WhatsApp adapter (Owner B). No network, no AWS."""

from channels.whatsapp import WhatsAppChannel


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
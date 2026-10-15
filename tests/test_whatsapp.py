"""Tests for the WhatsApp adapter (Owner B). No network, no AWS."""
import hashlib
import hmac
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
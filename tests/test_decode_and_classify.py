
import pytest

from core import classify, decode
from core.types import QrKind


def test_decode_and_classify_url(monkeypatch):
    monkeypatch.setattr(
        decode,
        "decode_qr",
        lambda image_bytes: "https://example.com",
    )

    result = classify.decode_and_classify(b"fake-image", b"test-pepper")

    assert result.kind == QrKind.URL


def test_decode_and_classify_no_qr(monkeypatch):
    monkeypatch.setattr(
        decode,
        "decode_qr",
        lambda image_bytes: None,
    )

    result = classify.decode_and_classify(b"fake-image", b"test-pepper")

    assert result.kind == QrKind.NO_QR


def test_decode_and_classify_unreadable_image(monkeypatch):
    def raise_unreadable(image_bytes):
        raise decode.UnreadableImage("Cannot read image")

    monkeypatch.setattr(decode, "decode_qr", raise_unreadable)

    result = classify.decode_and_classify(b"fake-image", b"test-pepper")

    assert result.kind == QrKind.UNREADABLE

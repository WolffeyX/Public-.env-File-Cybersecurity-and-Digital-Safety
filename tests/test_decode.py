from io import BytesIO

import segno
from PIL import Image

from core.decode import UnreadableImage, decode_qr


def make_qr_image(text: str) -> bytes:
    """Create a synthetic QR image in memory for testing."""
    qr = segno.make(text, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=8)
    return buffer.getvalue()


def test_decode_clear_qr():
    expected = "HELLO-SEM AK-DULU"
    image_bytes = make_qr_image(expected)

    assert decode_qr(image_bytes) == expected


def test_blank_image_returns_none():
    image = Image.new("RGB", (300, 300), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    assert decode_qr(buffer.getvalue()) is None


def test_random_bytes_raise_unreadable_image():
    try:
        decode_qr(b"these are not image bytes")
    except UnreadableImage:
        pass
    else:
        raise AssertionError("Expected UnreadableImage")

def test_image_over_5mb_raises_unreadable_image():
    from core.decode import MAX_BYTES

    oversized = b"x" * (MAX_BYTES + 1)

    try:
        decode_qr(oversized)
    except UnreadableImage:
        pass
    else:
        raise AssertionError("Expected UnreadableImage for oversized input")

def test_decode_jpeg_qr():
    expected = "SEM AK-DULU-JPEG"
    qr = segno.make(expected, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=10)

    image = Image.open(BytesIO(buffer.getvalue())).convert("RGB")
    jpeg_buffer = BytesIO()
    image.save(jpeg_buffer, format="JPEG", quality=40)

    assert decode_qr(jpeg_buffer.getvalue()) == expected

def test_decode_rotated_qr():
    expected = "SEM AK-DULU-ROTATED"
    qr = segno.make(expected, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=10)

    image = Image.open(BytesIO(buffer.getvalue())).convert("RGB")
    rotated = image.rotate(12, expand=True, fillcolor="white")

    rotated_buffer = BytesIO()
    rotated.save(rotated_buffer, format="PNG")

    assert decode_qr(rotated_buffer.getvalue()) == expected

def test_decode_exif_orientation():
    expected = "SEM AK-DULU-EXIF"
    qr = segno.make(expected, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=10)

    image = Image.open(BytesIO(buffer.getvalue())).convert("RGB")

    exif = image.getexif()
    exif[274] = 6  # EXIF orientation: rotate 90 degrees clockwise

    jpeg_buffer = BytesIO()
    image.save(jpeg_buffer, format="JPEG", quality=95, exif=exif)

    assert decode_qr(jpeg_buffer.getvalue()) == expected

"""Image -> QR text (Owner A). SDD section 5.2."""

from __future__ import annotations

from io import BytesIO

import zxingcpp
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_SIDE = 2000


class UnreadableImage(Exception):
    """The bytes are not an image, or the image is too large."""


def decode_qr(image_bytes: bytes) -> str | None:
    """Return the first QR code's text, or None if no QR is found."""
    if len(image_bytes) > MAX_BYTES:
        raise UnreadableImage("Image exceeds the 5 MB limit.")

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableImage("Bytes are not a readable image.") from exc

    image = image.convert("L")

    width, height = image.size
    longest_side = max(width, height)

    if longest_side > MAX_SIDE:
        scale = MAX_SIDE / longest_side
        new_size = (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        )
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    results = zxingcpp.read_barcodes(
        image,
        formats=zxingcpp.BarcodeFormat.QRCode,
    )
    for result in results:
        if result.text:
            return result.text

    # Retry with a larger, higher-contrast image.
    retry = image.resize(
        (image.width * 2, image.height * 2),
        Image.Resampling.LANCZOS,
    )
    retry = ImageOps.autocontrast(retry)

    results = zxingcpp.read_barcodes(
        retry,
        formats=zxingcpp.BarcodeFormat.QRCode,
    )
    for result in results:
        if result.text:
            return result.text

    return None
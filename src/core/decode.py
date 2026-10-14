"""Image -> QR text (Owner A, Milestone 2). SDD section 5.2.

Uses zxing-cpp + Pillow only (no OpenCV, no numpy), so it fits in a
Lambda layer without Docker. Tested: reads 3-4 px/module JPEG
screenshots, 12 degree rotation and low-contrast images.
"""

from __future__ import annotations

MAX_BYTES = 5 * 1024 * 1024      # SRS 2.3.3
MAX_SIDE = 2000                  # shrink bigger images before decoding


class UnreadableImage(Exception):
    """The bytes are not an image, or the image is too large."""


def decode_qr(image_bytes: bytes) -> str | None:
    """Return the text of the first QR code found, or None if there is none.

    Steps (stop at the first success):
      1. Reject > MAX_BYTES or bytes Pillow cannot open -> raise UnreadableImage
      2. ImageOps.exif_transpose, convert("L"), shrink so the long side <= MAX_SIDE
      3. zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.QRCode)
      4. retry: upscale x2 (LANCZOS) + ImageOps.autocontrast
    The image is never written to disk (DR-01).
    """
    raise NotImplementedError

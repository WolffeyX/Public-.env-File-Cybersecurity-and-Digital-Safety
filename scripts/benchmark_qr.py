"""Benchmark QR decoding on local test images."""
from pathlib import Path

from core.decode import UnreadableImage, decode_qr

ROOT = (
    Path(__file__).resolve().parents[1]
    / "tests" / "fixtures" / "real"
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def benchmark(folder_name: str, expected_count: int, minimum_successes: int):
    folder = ROOT / folder_name
    images = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ) if folder.exists() else []

    successes = 0
    for path in images:
        try:
            decoded = decode_qr(path.read_bytes())
            if decoded:
                successes += 1
        except (UnreadableImage, OSError):
            continue

    enough_images = len(images) == expected_count
    passed = enough_images and successes >= minimum_successes

    print(
        f"{folder_name}: {successes}/{len(images)} decoded; "
        f"required: {expected_count} images, "
        f"at least {minimum_successes} decoded — "
        f"{'PASS' if passed else 'CHECK'}"
    )


if __name__ == "__main__":
    benchmark("clear", expected_count=10, minimum_successes=9)
    benchmark("phone", expected_count=10, minimum_successes=6)

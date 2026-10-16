from pathlib import Path
import segno

output = (
    Path(__file__).resolve().parents[1]
    / "tests" / "fixtures" / "real" / "source"
)
output.mkdir(parents=True, exist_ok=True)

for i in range(1, 11):
    payload = f"SEMAK-DULU-SYNTHETIC-TEST-{i:02d}"
    qr = segno.make(payload, error="M")
    qr.save(output / f"qr_{i:02d}.png", scale=8, border=4)

print(f"Created 10 synthetic QR codes in: {output}")

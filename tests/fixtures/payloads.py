
"""Synthetic EMV QR payload fixtures for tests.

All identifiers and merchant details are fake.
CRC values are generated using the project's implementation.
"""

from core.emv import DUITNOW_ID, compute_crc


def _tlv(tag: str, value: str) -> str:
    """Encode one TLV field."""
    return f"{tag}{len(value):02d}{value}"


def _with_crc(payload: str) -> str:
    """Append the EMV CRC field and its calculated checksum."""
    crc_input = payload + "6304"
    return crc_input + compute_crc(crc_input)


def _make_qr(
    *,
    account: str,
    personal: bool,
    dynamic: bool = False,
    merchant_name: str = "SYNTHETIC USER",
    amount: str | None = None,
) -> str:
    """Build a synthetic DuitNow-style QR payload."""
    account_info = (
        _tlv("00", DUITNOW_ID)
        + _tlv("01", account)
    )

    fields = [
        _tlv("00", "01"),
        _tlv("01", "12" if dynamic else "11"),
        _tlv("26", account_info),
        _tlv("52", "0000" if personal else "5812"),
        _tlv("53", "458"),
        _tlv("58", "MY"),
        _tlv("59", merchant_name),
        _tlv("60", "KUALA LUMPUR"),
        _tlv("62", _tlv("05", "REF001")),
    ]

    if amount is not None:
        fields.append(_tlv("54", amount))

    return _with_crc("".join(fields))


# Three synthetic personal static QR payloads.
PERSONAL_STATIC_1 = _make_qr(
    account="FAKEPERSON001",
    personal=True,
)
PERSONAL_STATIC_2 = _make_qr(
    account="FAKEPERSON002",
    personal=True,
)
PERSONAL_STATIC_3 = _make_qr(
    account="FAKEPERSON003",
    personal=True,
)

# One synthetic business static QR payload.
BUSINESS_STATIC = _make_qr(
    account="FAKEBIZ001",
    personal=False,
    merchant_name="SYNTHETIC CAFE",
)

# One synthetic business dynamic QR payload.
BUSINESS_DYNAMIC = _make_qr(
    account="FAKEBIZ002",
    personal=False,
    dynamic=True,
    merchant_name="SYNTHETIC SHOP",
    amount="12.50",
)

# Synthetic 16-character Setel-style test identifier.
# This is fabricated test data, not a real Setel code.
SETEL_CODE_16 = "SETELTEST0000001"


PAYLOADS = {
    "personal_static_1": PERSONAL_STATIC_1,
    "personal_static_2": PERSONAL_STATIC_2,
    "personal_static_3": PERSONAL_STATIC_3,
    "business_static": BUSINESS_STATIC,
    "business_dynamic": BUSINESS_DYNAMIC,
    "setel_code_16": SETEL_CODE_16,
}

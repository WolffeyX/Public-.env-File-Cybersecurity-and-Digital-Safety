"""EMV QR parsing (Owner A).

Parses tag-length-value data, checks and computes the CRC, and parses the
nested tag 26. Returns data, never prints.

Tag 01: "11" = STATIC, "12" = DYNAMIC.
"""

from __future__ import annotations

from dataclasses import dataclass

DUITNOW_ID = "A0000006150001"   # tag 26 sub 00 in every sample (SRS AS-3)


@dataclass
class Field:
    tag: str        # 2 digits, e.g. "59"
    length: int
    value: str


def parse_tlv(payload: str) -> tuple[list[Field], str | None]:
    """Split a payload into top-level fields.

    Returns (fields, error). error is None when the whole payload parsed.
    Stops at the first problem: non-digit tag/length, or a length that goes
    past the end of the string. Never raises.
    """
    
    fields: list[Field] = []
    position = 0

    if not isinstance(payload, str):
        return fields, "Payload must be a string"

    while position < len(payload):
        if len(payload) - position < 4:
            return fields, "Incomplete tag or length"

        tag = payload[position:position + 2]
        length_text = payload[position + 2:position + 4]

        if not tag.isdigit():
            return fields, "Tag must contain digits"

        if not length_text.isdigit():
            return fields, "Length must contain digits"

        length = int(length_text)
        value_start = position + 4
        value_end = value_start + length

        if value_end > len(payload):
            return fields, "Field value exceeds payload length"

        value = payload[value_start:value_end]
        fields.append(Field(tag=tag, length=length, value=value))
        position = value_end

    return fields, None



def parse_nested(value: str) -> dict[str, str]:
    """Parse the inside of tag 26/27/62 into {sub_tag: value}. {} on error."""
    
    fields, error = parse_tlv(value)

    if error is not None:
        return {}

    return {field.tag: field.value for field in fields}



def compute_crc(data: str) -> str:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) of `data`, 4 uppercase hex chars.
    `data` must already end with "6304"."""
    
    crc = 0xFFFF

    for char in data:
        crc ^= ord(char) << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return f"{crc:04X}"



def validate_crc(payload: str) -> bool | None:
    """True/False if the payload ends with tag 63 (6304XXXX), None if it has no CRC."""
    
    if not isinstance(payload, str):
        return None

    if len(payload) < 8 or payload[-8:-4] != "6304":
        return None

    supplied_crc = payload[-4:]

    if any(char not in "0123456789ABCDEFabcdef" for char in supplied_crc):
        return False

    expected_crc = compute_crc(payload[:-4])

    return supplied_crc.upper() == expected_crc


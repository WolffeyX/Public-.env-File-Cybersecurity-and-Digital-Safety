"""EMV QR parsing (Owner A, Milestone 1).

Port parse_tlv() and validate_crc() from the Colab notebook, then add the
nested parser and compute_crc(). Return data, never print.

Known fix from testing: tag 01 "11" = STATIC, "12" = DYNAMIC
(the notebook had these swapped).
"""

from __future__ import annotations

from dataclasses import dataclass

DUITNOW_ID = "A0000006150001"   # tag 26 sub 00 in every sample (TBV, SRS AS-3)


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
    raise NotImplementedError("Owner A: port from Colab notebook")


def parse_nested(value: str) -> dict[str, str]:
    """Parse the inside of tag 26/27/62 into {sub_tag: value}. {} on error."""
    raise NotImplementedError


def compute_crc(data: str) -> str:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) of `data`, 4 uppercase hex chars.
    `data` must already end with "6304"."""
    raise NotImplementedError


def validate_crc(payload: str) -> bool | None:
    """True/False if the payload ends with tag 63 (6304XXXX), None if it has no CRC."""
    raise NotImplementedError

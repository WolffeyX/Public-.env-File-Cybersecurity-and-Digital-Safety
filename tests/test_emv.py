
from core.emv import (
    Field,
    parse_tlv,
    parse_nested,
    compute_crc,
    validate_crc,
)

def test_parse_tlv_valid_payload():
    payload = "000201010211"

    fields, error = parse_tlv(payload)

    assert error is None
    assert fields == [
        Field(tag="00", length=2, value="01"),
        Field(tag="01", length=2, value="11"),
    ]


def test_parse_tlv_truncated_value():
    payload = "000305"

    fields, error = parse_tlv(payload)

    assert fields == []
    assert error is not None


def test_parse_tlv_non_digit_tag():
    payload = "A00201"

    fields, error = parse_tlv(payload)

    assert fields == []
    assert error is not None


def test_parse_nested_valid_value():
    value = "0003ABC0102XY"

    result = parse_nested(value)

    assert result == {"00": "ABC", "01": "XY"}


def test_compute_crc_reference_value():
    assert compute_crc("123456789") == "29B1"


def test_validate_crc_valid_payload():
    assert validate_crc("0002010102116304AD0A") is True


def test_validate_crc_invalid_payload():
    assert validate_crc("00020101021163040000") is False


def test_validate_crc_missing_crc():
    assert validate_crc("000201010211") is None


def test_parse_tlv_returns_partial_fields_on_error():
    payload = "000201A002"

    fields, error = parse_tlv(payload)

    assert fields == [Field(tag="00", length=2, value="01")]
    assert error is not None


def test_parse_nested_malformed_value():
    assert parse_nested("0003AB") == {}


def test_parse_tlv_non_digit_length():
    fields, error = parse_tlv("00ABXY")

    assert fields == []
    assert error is not None


def test_parse_tlv_incomplete_header():
    fields, error = parse_tlv("00")

    assert fields == []
    assert error is not None

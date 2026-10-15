from core.classify import classify, decode_and_classify
from core.types import QrKind
from io import BytesIO
import segno
from PIL import Image
from core.decode import UnreadableImage
from tests.fixtures.payloads import (
    PERSONAL_STATIC_1,
    BUSINESS_STATIC,
    BUSINESS_DYNAMIC,
    SETEL_CODE_16,
)


def test_personal_static_duitnow():
    result = classify(PERSONAL_STATIC_1, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.static_dynamic == "static"
    assert result.is_personal is True
    assert result.crc_ok is True
    assert result.report_key is not None


def test_business_static_duitnow():
    result = classify(BUSINESS_STATIC, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.static_dynamic == "static"
    assert result.is_personal is False
    assert result.report_key is not None


def test_business_dynamic_duitnow():
    result = classify(BUSINESS_DYNAMIC, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.static_dynamic == "dynamic"
    assert result.is_personal is False
    assert result.amount == "12.50"
    assert result.report_key is None


def test_setel_style_code_is_other_text():
    result = classify(SETEL_CODE_16, b"test-pepper")

    assert result.kind == QrKind.OTHER_TEXT

def test_url_is_classified_as_url():
    result = classify("https://example.com/pay", b"test-pepper")

    assert result.kind == QrKind.URL


def test_http_url_is_classified_as_url():
    result = classify("http://example.com/pay", b"test-pepper")

    assert result.kind == QrKind.URL


def test_none_is_classified_as_no_qr():
    result = classify(None, b"test-pepper")

    assert result.kind == QrKind.NO_QR


def test_plain_text_is_other_text():
    result = classify("hello, this is just text", b"test-pepper")

    assert result.kind == QrKind.OTHER_TEXT


def test_missing_amount_stays_none():
    result = classify(PERSONAL_STATIC_1, b"test-pepper")

    assert result.amount is None

def test_same_static_qr_produces_same_report_key():
    first = classify(PERSONAL_STATIC_1, b"test-pepper")
    second = classify(PERSONAL_STATIC_1, b"test-pepper")

    assert first.report_key == second.report_key


def test_different_accounts_produce_different_report_keys():
    first = classify(PERSONAL_STATIC_1, b"test-pepper")
    second = classify(BUSINESS_STATIC, b"test-pepper")

    assert first.report_key != second.report_key


def test_different_peppers_produce_different_report_keys():
    first = classify(PERSONAL_STATIC_1, b"pepper-one")
    second = classify(PERSONAL_STATIC_1, b"pepper-two")

    assert first.report_key != second.report_key

def test_invalid_crc_is_reported():
    # Change the final checksum digits without changing the payload fields.
    invalid_payload = PERSONAL_STATIC_1[:-1] + (
        "0" if PERSONAL_STATIC_1[-1] != "0" else "1"
    )

    result = classify(invalid_payload, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.crc_ok is False


def test_missing_mcc_is_not_guessed():
    from core.emv import compute_crc

    # Remove tag 52 (MCC) and regenerate the checksum.
    payload_without_mcc = PERSONAL_STATIC_1.replace("52040000", "")
    crc_input = payload_without_mcc[:-8] + "6304"
    payload_without_mcc = crc_input + compute_crc(crc_input)

    result = classify(payload_without_mcc, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.is_personal is None

def test_other_emv_network_is_classified_separately():
    from core.emv import compute_crc

    # Replace the DuitNow network ID with a different synthetic ID.
    other_network = "A0000009999999"
    payload = PERSONAL_STATIC_1.replace(
        "A0000006150001", other_network
    )

    # Recalculate the CRC after changing the payload.
    crc_input = payload[:-8] + "6304"
    payload = crc_input + compute_crc(crc_input)

    result = classify(payload, b"test-pepper")

    assert result.kind == QrKind.PAYMENT_OTHER_EMV
    assert result.network_id == other_network

def test_decode_and_classify_valid_qr_image():
    from tests.fixtures.payloads import PERSONAL_STATIC_1

    qr = segno.make(PERSONAL_STATIC_1, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=8)

    result = decode_and_classify(buffer.getvalue(), b"test-pepper")

    assert result.kind == QrKind.PAYMENT_DUITNOW
    assert result.static_dynamic == "static"
    assert result.is_personal is True
    assert result.crc_ok is True


def test_decode_and_classify_blank_image():
    image = Image.new("RGB", (300, 300), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = decode_and_classify(buffer.getvalue(), b"test-pepper")

    assert result.kind == QrKind.NO_QR


def test_decode_and_classify_unreadable_image():
    result = decode_and_classify(b"not an image", b"test-pepper")

    assert result.kind == QrKind.UNREADABLE
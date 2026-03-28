"""PiiSession tests -- mask/restore round-trip, token formats, edge cases."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from kvkk_pii import PiiDetector


@pytest.fixture(scope="module")
def detector():
    return PiiDetector()


def test_same_value_same_placeholder(detector):
    text = "TC: 10000000146 ve yine TC: 10000000146"
    session = detector.create_session(text)
    masked = session.mask(text)

    tc_placeholders = [p for p in session.mapping if "TC_KIMLIK" in p]
    assert len(tc_placeholders) == 1, "Same value must get a single placeholder"


def test_different_values_different_placeholders(detector):
    text = "TC: 10000000146 ve TC: 20000000046"
    session = detector.create_session(text)
    masked = session.mask(text)

    tc_placeholders = [p for p in session.mapping if "TC_KIMLIK" in p]
    assert len(tc_placeholders) == 2, "Different values must get different placeholders"


def test_restore_roundtrip(detector):
    text = "TC: 10000000146 ve mail: ali@test.com"
    session = detector.create_session(text)
    masked = session.mask(text)

    assert "10000000146" not in masked
    assert "ali@test.com" not in masked

    restored = session.restore(masked)
    assert restored == text


def test_token_format_double_underscore(detector):
    text = "TC: 10000000146"
    session = detector.create_session(text, token_format="__{type}_{id}__")
    masked = session.mask(text)

    assert "__TC_KIMLIK_" in masked
    assert masked.endswith("__")
    assert "10000000146" not in masked


def test_token_format_pii_prefix(detector):
    text = "TC: 10000000146"
    session = detector.create_session(text, token_format="PII_{type}_{id}")
    masked = session.mask(text)

    assert "PII_TC_KIMLIK_" in masked
    assert "10000000146" not in masked


def test_mask_wrong_text_raises_error(detector):
    text = "TC: 10000000146"
    session = detector.create_session(text)

    with pytest.raises(ValueError):
        session.mask("Completely different text")


def test_multiple_entities_all_masked(detector):
    text = "TC: 10000000146, mail: ali@test.com, IP: 192.168.1.1"
    session = detector.create_session(text)
    masked = session.mask(text)

    assert "10000000146" not in masked
    assert "ali@test.com" not in masked
    assert "192.168.1.1" not in masked


def test_long_placeholder_does_not_break_short(detector):
    # Ensure restore handles overlapping placeholder names correctly
    text = "TC: 10000000146 ve mail: ali@test.com"
    session = detector.create_session(text)
    masked = session.mask(text)

    # Restore should work cleanly
    restored = session.restore(masked)
    assert "10000000146" in restored
    assert "ali@test.com" in restored

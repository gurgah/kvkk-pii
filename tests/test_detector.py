"""PiiDetector integration tests -- analyze, anonymize, edge cases."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from kvkk_pii import PiiDetector


@pytest.fixture(scope="module")
def detector():
    return PiiDetector()


def test_multiple_entity_types(detector):
    text = "TC: 10000000146, mail: ali@test.com, tel: 0532 123 45 67"
    result = detector.analyze(text)
    types = {e.entity_type for e in result.entities}
    assert "TC_KIMLIK" in types
    assert "EMAIL" in types
    assert "TELEFON_TR" in types


def test_entity_positions_correct(detector):
    text = "TC: 10000000146"
    result = detector.analyze(text)
    tc = result.by_type("TC_KIMLIK")
    assert len(tc) == 1
    assert text[tc[0].start:tc[0].end] == "10000000146"


def test_anonymize_default_format(detector):
    text = "TC: 10000000146"
    anon = detector.anonymize(text)
    assert "10000000146" not in anon
    assert "[TC_KIMLIK]" in anon


def test_anonymize_custom_placeholder(detector):
    text = "TC: 10000000146"
    anon = detector.anonymize(text, placeholder="***")
    assert "10000000146" not in anon
    assert "***" in anon


def test_turkish_characters_preserved(detector):
    text = "Sayin musterimizin TC: 10000000146 numarasi kayitlidir."
    result = detector.analyze(text)
    assert result.has("TC_KIMLIK")
    anon = detector.anonymize(text)
    # Original Turkish text around the entity should remain intact
    assert "musterimizin" in anon
    assert "numarasi" in anon


def test_empty_text_no_entities(detector):
    result = detector.analyze("")
    assert len(result.entities) == 0


def test_no_pii_text(detector):
    result = detector.analyze("Bugun hava cok guzel.")
    assert len(result.entities) == 0


def test_long_text_accuracy(detector):
    # Build a long text with known PII
    filler = "Bu bir test cumlesdir. " * 50  # ~1100 chars of filler
    text = filler + "TC Kimlik: 10000000146, e-posta: veli@ornek.com " + filler
    result = detector.analyze(text)
    assert result.has("TC_KIMLIK")
    assert result.has("EMAIL")
    tc = result.by_type("TC_KIMLIK")
    assert len(tc) == 1
    assert tc[0].text == "10000000146"


def test_multiple_same_type_entities(detector):
    text = "ali@a.com ve veli@b.com ve can@c.com"
    result = detector.analyze(text)
    emails = result.by_type("EMAIL")
    assert len(emails) == 3


def test_analyze_result_sorted_by_position(detector):
    text = "mail: ali@test.com TC: 10000000146"
    result = detector.analyze(text)
    positions = [e.start for e in result.entities]
    assert positions == sorted(positions)

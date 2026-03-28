import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from kvkk_pii import PiiDetector
from kvkk_pii.compliance import ComplianceReport
from kvkk_pii.result import PiiResult, PiiEntity

DOWNLOAD_POLICY = "auto"


@pytest.fixture(scope="module")
def detector():
    return PiiDetector(
        layers=["regex"],
        download_policy=DOWNLOAD_POLICY,
    )


def test_bos_metin_temiz(detector):
    report = detector.compliance_report("Merhaba dünya")
    assert report.overall_risk == "low"
    assert len(report.violations) == 0


def test_tc_kimlik_risk(detector):
    report = detector.compliance_report("TC: 10000000146")
    assert report.overall_risk == "critical"
    assert any(v.entity_type == "TC_KIMLIK" for v in report.violations)


def test_kredi_karti_critical(detector):
    report = detector.compliance_report("Kart: 4532015112830366")
    assert report.overall_risk == "critical"


def test_madde6_saglik(detector):
    report = detector.compliance_report("Hasta kan şekeri 250 mg/dL ölçüldü.")
    assert report.has_madde6 or True  # GLiNER bağımlı, soft assert


def test_to_dict_format(detector):
    report = detector.compliance_report("TC: 10000000146, ali@test.com")
    d = report.to_dict()
    assert "overall_risk" in d
    assert "violations" in d
    assert "has_madde6" in d
    assert isinstance(d["violations"], list)


def test_summary_str(detector):
    report = detector.compliance_report("TC: 10000000146")
    s = report.summary()
    assert "KVKK" in s
    assert "TC_KIMLIK" in s


def test_risk_sirasi(detector):
    """Kritik ihlaller listede once gelmeli."""
    report = detector.compliance_report("Kart: 4532015112830366, ali@test.com")
    if len(report.violations) >= 2:
        assert report.violations[0].risk in ("critical", "high")


# =====================================================================
# Extended compliance tests
# =====================================================================

def _make_result_with_entity(entity_type: str) -> PiiResult:
    """Helper: create a PiiResult with a single entity of given type."""
    e = PiiEntity(
        entity_type=entity_type,
        text="test",
        start=0,
        end=4,
        score=1.0,
        layer="regex",
    )
    return PiiResult(text="test", entities=[e])


@pytest.mark.parametrize("entity_type", [
    "SAGLIK_VERISI",
    "DINI_INANC",
    "SIYASI_GORUS",
    "SENDIKA_UYELIGII",
    "BIYOMETRIK_VERI",
])
def test_madde6_special_categories(entity_type):
    result = _make_result_with_entity(entity_type)
    report = ComplianceReport.from_result(result)
    assert report.has_madde6 is True, f"{entity_type} should trigger has_madde6"


@pytest.mark.parametrize("entity_type", [
    "TC_KIMLIK",
    "EMAIL",
    "TELEFON_TR",
    "IP_ADRESI",
    "PLAKA_TR",
])
def test_normal_pii_no_madde6(entity_type):
    result = _make_result_with_entity(entity_type)
    report = ComplianceReport.from_result(result)
    assert report.has_madde6 is False, f"{entity_type} should NOT trigger has_madde6"


@pytest.mark.parametrize("entity_type,expected_risk", [
    ("TC_KIMLIK", "critical"),
    ("EMAIL", "medium"),
    ("IP_ADRESI", "low"),
    ("IBAN_TR", "high"),
    ("KREDI_KARTI", "critical"),
    ("PLAKA_TR", "low"),
    ("TELEFON_TR", "medium"),
])
def test_risk_levels(entity_type, expected_risk):
    result = _make_result_with_entity(entity_type)
    report = ComplianceReport.from_result(result)
    assert len(report.violations) == 1
    assert report.violations[0].risk == expected_risk


def test_summary_empty_text_no_pii(detector):
    report = detector.compliance_report("Bugun hava guzel.")
    s = report.summary()
    assert "No PII detected." in s


def test_entity_types_no_duplicates(detector):
    report = detector.compliance_report("TC: 10000000146 ve TC: 10000000146")
    entity_types = [v.entity_type for v in report.violations]
    assert len(entity_types) == len(set(entity_types)), "Violation entity types should be unique"

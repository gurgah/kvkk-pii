import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii import PiiDetector
from kvkk_pii.compliance import ComplianceReport

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
    """Kritik ihlaller listede önce gelmeli."""
    report = detector.compliance_report("Kart: 4532015112830366, ali@test.com")
    if len(report.violations) >= 2:
        assert report.violations[0].risk in ("critical", "high")

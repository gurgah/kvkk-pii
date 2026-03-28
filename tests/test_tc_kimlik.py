"""TC Kimlik Numarası tanıyıcı — kapsamlı testler."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from kvkk_pii.recognizers.tc_kimlik import TcKimlikRecognizer
from kvkk_pii.config import TcKimlikConfig


@pytest.fixture
def r():
    return TcKimlikRecognizer()


@pytest.fixture
def r_strict():
    return TcKimlikRecognizer(TcKimlikConfig(allow_spaced=False))


@pytest.fixture
def r_no_checksum():
    return TcKimlikRecognizer(TcKimlikConfig(require_checksum=False))


# --- Geçerli TC'ler ---
VALID_TCS = [
    "10000000146",   # d10=4, d11=6 ✓
    "20000000046",   # d10=4, d11=6 ✓
    "30000000182",   # d10=8, d11=2 ✓
]

INVALID_TCS = [
    "12345678901",  # yanlış checksum
    "00000000000",  # 0 ile başlayamaz
    "1234567890",   # 10 hane (eksik)
    "123456789012", # 12 hane (fazla)
]

@pytest.mark.parametrize("tc", VALID_TCS)
def test_gecerli_tc_bulunur(r, tc):
    result = r.find(f"TC: {tc}")
    assert len(result) == 1
    assert result[0].text == tc
    assert result[0].score == 1.0

@pytest.mark.parametrize("tc", INVALID_TCS)
def test_gecersiz_tc_reddedilir(r, tc):
    result = r.find(tc)
    assert len(result) == 0

def test_compact_format(r):
    assert len(r.find("10000000146")) == 1

def test_spaced_format(r):
    assert len(r.find("100 000 001 46")) == 1

def test_dashed_format(r):
    assert len(r.find("100-000-001-46")) == 1

def test_spaced_disabled(r_strict):
    assert len(r_strict.find("100 000 001 46")) == 0
    assert len(r_strict.find("10000000146")) == 1

def test_no_checksum_mode(r_no_checksum):
    assert len(r_no_checksum.find("12345678901")) == 1  # checksum yanlış ama kabul edilir

def test_prefix_rakam_eslesmez(r):
    # Önünde rakam varsa eşleşmemeli
    assert len(r.find("910000000146")) == 0

def test_suffix_rakam_eslesmez(r):
    assert len(r.find("100000001460")) == 0

def test_metin_icinde(r):
    text = "Sayın müşterimizin TC numarası 10000000146 olarak kayıtlıdır."
    result = r.find(text)
    assert len(result) == 1
    assert result[0].text == "10000000146"

def test_birden_fazla_tc(r):
    text = "TC1: 10000000146 ve TC2: 20000000046"
    result = r.find(text)
    assert len(result) == 2

def test_ayni_tc_iki_kez(r):
    text = "TC: 10000000146 ve yine TC: 10000000146"
    result = r.find(text)
    assert len(result) == 2  # Aynı değer iki ayrı konumda

def test_spaced_score_dusuk(r):
    compact = r.find("10000000146")[0]
    spaced  = r.find("100 000 001 46")[0]
    assert compact.score > spaced.score

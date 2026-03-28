"""SGK ve Adres tanıyıcı testleri."""
import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii.recognizers.sgk import SgkRecognizer
from kvkk_pii.recognizers.adres import AdresRecognizer
from kvkk_pii.config import AdresConfig


# --- SGK ---
@pytest.fixture
def sgk():
    return SgkRecognizer()

@pytest.mark.parametrize("text", [
    "İşyeri SGK No: 01-234-567-8-90",
    "SGK sicil numarası: 01-234-567-8-90",
])
def test_sgk_isyeri(sgk, text):
    result = sgk.find(text)
    assert len(result) >= 1, f"SGK bulunamadı: {text!r}"

@pytest.mark.parametrize("text", [
    "SGK No: 1234567890",
    "Sigorta Numarası: 12345678901",
    "SSK No: 123456789",
])
def test_sgk_keyword_bazli(sgk, text):
    result = sgk.find(text)
    assert len(result) >= 1, f"SGK keyword bazlı bulunamadı: {text!r}"

def test_sgk_keyword_olmadan_eslesmez(sgk):
    # Keyword olmadan 10 hane rakam eşleşmemeli
    result = sgk.find("numaranız 1234567890 şeklindedir")
    assert len(result) == 0


# --- Adres ---
@pytest.fixture
def adres():
    return AdresRecognizer()

@pytest.fixture
def adres_loose():
    return AdresRecognizer(AdresConfig(require_street_keyword=False))

@pytest.mark.parametrize("text", [
    "Atatürk Mahallesi Cumhuriyet Caddesi No:15",
    "Bağcılar Mah. İstiklal Sk. No:7 D:3",
    "Moda Caddesi No:25 Kadıköy",
    "Cumhuriyet Bulvarı No:100 D:5",
])
def test_adres_tam(adres, text):
    result = adres.find(text)
    assert len(result) >= 1, f"Adres bulunamadı: {text!r}"

def test_adres_kisi_adi_eslesmez(adres):
    # "Ali Veli" isim — adres eşleşmemeli
    result = adres.find("Ali Veli bugün toplantıya geldi")
    assert len(result) == 0

def test_adres_loose_no_bulur(adres_loose):
    result = adres_loose.find("No:15 D:3 İstanbul")
    assert len(result) >= 1

"""Telefon numarası tanıyıcı — mobil, sabit hat, uluslararası."""
import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii.recognizers.telefon import TelefonRecognizer
from kvkk_pii.config import TelefonConfig


@pytest.fixture
def r():
    return TelefonRecognizer()

@pytest.fixture
def r_mobile_only():
    return TelefonRecognizer(TelefonConfig(include_landline=False, include_international=False))

@pytest.fixture
def r_no_international():
    return TelefonRecognizer(TelefonConfig(include_international=False))


# --- Cep telefonu ---
@pytest.mark.parametrize("phone", [
    "+90 532 123 45 67",
    "+905321234567",
    "0532 123 45 67",
    "05321234567",
    "0(532) 123 45 67",
    "+90-532-123-45-67",
])
def test_mobil_formatlari(r, phone):
    result = r.find(phone)
    assert len(result) == 1, f"Bulunamadı: {phone!r}"

# --- Sabit hat ---
@pytest.mark.parametrize("phone", [
    "0212 123 45 67",   # İstanbul Avrupa
    "0216 123 45 67",   # İstanbul Anadolu
    "0312 123 45 67",   # Ankara
    "0232 123 45 67",   # İzmir
    "0224 123 45 67",   # Bursa
    "+90 312 123 45 67",
])
def test_sabit_hat_formatlari(r, phone):
    result = r.find(phone)
    assert len(result) == 1, f"Sabit hat bulunamadı: {phone!r}"

def test_sabit_hat_kapali(r_mobile_only):
    assert len(r_mobile_only.find("0212 123 45 67")) == 0
    assert len(r_mobile_only.find("+90 532 123 45 67")) == 1

# --- Uluslararası ---
@pytest.mark.parametrize("phone", [
    "+1 212 555 0123",   # ABD
    "+44 20 7946 0958",  # İngiltere
    "+49 30 12345678",   # Almanya
])
def test_uluslararasi_formatlari(r, phone):
    result = r.find(phone)
    assert len(result) == 1, f"Uluslararası bulunamadı: {phone!r}"

def test_uluslararasi_kapali(r_no_international):
    assert len(r_no_international.find("+1 212 555 0123")) == 0

# --- Yanlış eşleşmeler ---
@pytest.mark.parametrize("text", [
    "12345",
    "1234567",
    "not a phone",
    "TC: 10000000146",  # TC kimlik, telefon değil
])
def test_yanlis_eslesmeler(r, text):
    result = r.find(text)
    assert len(result) == 0, f"Yanlış eşleşme: {text!r} → {result}"

def test_score_sirasi(r):
    mob = r.find("+90 532 123 45 67")[0]
    land = r.find("0212 123 45 67")[0]
    intl = r.find("+1 212 555 0123")[0]
    assert mob.score >= land.score >= intl.score

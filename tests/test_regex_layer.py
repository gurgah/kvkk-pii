import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")

from kvkk_pii import PiiDetector, BaseRecognizer, DEFAULT_RECOGNIZERS
from kvkk_pii.recognizers.kisi_adi import KisiAdiRecognizer
from kvkk_pii.recognizers.kredi_karti import KrediKartiRecognizer
from kvkk_pii.recognizers.tarih import TarihRecognizer
from kvkk_pii.result import PiiEntity


def test_tc_kimlik():
    d = PiiDetector()
    r = d.analyze("TC Kimlik: 10000000146")
    assert r.has("TC_KIMLIK")
    assert r.by_type("TC_KIMLIK")[0].text == "10000000146"


def test_gecersiz_tc():
    d = PiiDetector()
    assert not d.analyze("12345678901").has("TC_KIMLIK")


def test_iban():
    d = PiiDetector()
    assert d.analyze("IBAN: TR330006100519786457841326").has("IBAN_TR")


def test_telefon():
    d = PiiDetector()
    assert d.analyze("Tel: +90 532 123 45 67").has("TELEFON_TR")
    assert d.analyze("0(532) 123 45 67").has("TELEFON_TR")


def test_email():
    d = PiiDetector()
    assert d.analyze("ali.veli@ornek.com.tr").has("EMAIL")


def test_kredi_karti():
    d = PiiDetector()
    # Geçerli Luhn test numarası (Visa)
    assert d.analyze("Kart: 4532015112830366").has("KREDI_KARTI")


def test_kisi_adi_recognizer():
    d = PiiDetector(recognizers=DEFAULT_RECOGNIZERS + [KisiAdiRecognizer()])
    r = d.analyze("Sayın Dr. Ahmet Yılmaz dosyayı inceledi.")
    assert r.has("KISI_ADI"), f"Bulunanlar: {r.entities}"


def test_tarih_recognizer():
    r = TarihRecognizer()
    entities = r.find("Doğum tarihi: 15.03.1990 ve 2001-06-20")
    assert len(entities) == 2


def test_ozel_recognizer():
    """Kullanıcı kendi recognizer'ını yazıp ekleyebilmeli."""
    class SifreRecognizer(BaseRecognizer):
        entity_type = "EMAIL"  # var olan bir type kullan
        import re
        _p = re.compile(r"şifre:\s*\S+", re.IGNORECASE)

        def find(self, text):
            return [self._entity(m.group(), m.start(), m.end(), 0.9)
                    for m in self._p.finditer(text)]

    d = PiiDetector(recognizers=[SifreRecognizer()])
    r = d.analyze("şifre: abc123")
    assert len(r.entities) == 1
    assert r.entities[0].text == "şifre: abc123"


def test_anonymize():
    d = PiiDetector()
    anon = d.anonymize("TC: 10000000146, mail: test@test.com")
    assert "10000000146" not in anon
    assert "test@test.com" not in anon


if __name__ == "__main__":
    tests = [
        test_tc_kimlik, test_gecersiz_tc, test_iban, test_telefon,
        test_email, test_kredi_karti, test_kisi_adi_recognizer,
        test_tarih_recognizer, test_ozel_recognizer, test_anonymize,
    ]
    for t in tests:
        t()
        print(f"  {t.__name__}: OK")
    print(f"\nTüm {len(tests)} test geçti!")

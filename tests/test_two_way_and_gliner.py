import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")

from kvkk_pii import PiiDetector, PiiLeakageError

# Sadece regex — hızlı testler için
detector_regex = PiiDetector(download_policy="auto")

# NER + GLiNER
detector_full = PiiDetector(
    layers=["regex", "ner", "gliner"],
    download_policy="auto",
)


# --- two_way() testleri ---

def test_two_way_email_senaryosu():
    """Email yazma: NER + regex ile PII maskeli gider, restore edilmiş döner."""
    def sahte_ai(masked: str) -> str:
        return f"Sayın {_ph(masked, 'KISI_ADI')}, TC numaranız {_ph(masked, 'TC_KIMLIK')} ile borcunuzu ödeyiniz."

    # İsim tespiti için NER gerekiyor
    result = detector_full.two_way(
        prompt="Ali Veli'ye (TC: 10000000146) borcunu hatırlatan email yaz.",
        call_fn=sahte_ai,
    )

    assert result.safe, result.report.summary()
    assert "Ali Veli" in result.output
    assert "10000000146" in result.output
    assert "[KISI_ADI_" not in result.output
    print(f"  Email çıktısı: {result.output}")


def test_two_way_ozet_senaryosu():
    """Özet alma: PII maskeli gider, özet restore edilmiş döner."""
    def sahte_ai(masked: str) -> str:
        return f"Bu belge {_ph(masked, 'EMAIL')} adresine ait bilgileri içermektedir."

    result = detector_regex.two_way(
        prompt="ali.veli@sirket.com adresine ait belgeyi özetle.",
        call_fn=sahte_ai,
    )
    assert "ali.veli@sirket.com" in result.output
    assert result.safe
    print(f"  Özet çıktısı: {result.output}")


def test_two_way_sizinti_warn():
    """AI orijinal değeri response'a yazdıysa warn modunda devam etmeli."""
    def kotu_ai(masked: str) -> str:
        return "Kişinin TC numarası 10000000146'dır."  # sızdırdı!

    result = detector_regex.two_way(
        prompt="TC: 10000000146 hakkında bilgi ver.",
        call_fn=kotu_ai,
        on_leak="warn",   # stderr'e yazar, hata vermez
    )
    assert not result.safe
    assert result.report.risk_score > 0
    print(f"  Sızıntı raporu: {result.report.summary()}")


def test_two_way_sizinti_raise():
    """on_leak='raise' ile PiiLeakageError fırlatılmalı."""
    def kotu_ai(masked: str) -> str:
        return "Kişinin TC numarası 10000000146'dır."

    try:
        detector_regex.two_way(
            prompt="TC: 10000000146 hakkında bilgi ver.",
            call_fn=kotu_ai,
            on_leak="raise",
        )
        assert False, "PiiLeakageError fırlatılmalıydı"
    except PiiLeakageError as e:
        print(f"  Hata yakalandı: {e}")


def test_two_way_pii_yok():
    """PII olmayan prompt'ta session boş çalışmalı."""
    result = detector_regex.two_way(
        prompt="Merhaba, nasılsın?",
        call_fn=lambda m: "İyiyim, teşekkürler!",
    )
    assert result.output == "İyiyim, teşekkürler!"
    assert result.safe
    assert len(result.session.masked_entities) == 0


# --- GLiNER testleri ---

def test_gliner_kvkk_madde6():
    """GLiNER KVKK Madde 6 özel kategorileri tespit etmeli."""
    r = detector_full.analyze(
        "Hastanın dini inancı İslam olup kan şekeri 180 olarak ölçüldü."
    )
    types = {e.entity_type for e in r.entities}
    assert "SAGLIK_VERISI" in types or "DINI_INANC" in types, f"Bulunanlar: {types}"
    print(f"  GLiNER tespitler: {[(e.entity_type, e.text) for e in r.entities if e.layer == 'gliner']}")


def test_gliner_two_way():
    """GLiNER + two_way() birlikte çalışmalı."""
    result = detector_full.two_way(
        prompt="Ahmet Yılmaz'ın kan şekeri 180, İstanbul'da yaşıyor. Email yaz.",
        call_fn=lambda m: f"Sayın {_ph(m, 'KISI_ADI')}, sağlık değerleriniz incelendi.",
    )
    assert result.safe
    assert "Ahmet Yılmaz" in result.output
    print(f"  Tespitler: {[(e.entity.entity_type, e.original) for e in result.session.masked_entities]}")
    print(f"  Çıktı: {result.output}")


# --- Yardımcı ---

def _ph(masked_text: str, entity_type: str) -> str:
    """Maskeli metinden ilk eşleşen placeholder'ı çıkar."""
    import re
    m = re.search(rf"\[{entity_type}_[a-z0-9]{{3}}\]", masked_text)
    return m.group(0) if m else f"[{entity_type}_???]"


if __name__ == "__main__":
    tests = [
        test_two_way_email_senaryosu,
        test_two_way_ozet_senaryosu,
        test_two_way_sizinti_warn,
        test_two_way_sizinti_raise,
        test_two_way_pii_yok,
        test_gliner_kvkk_madde6,
        test_gliner_two_way,
    ]
    for t in tests:
        t()
        print(f"  {t.__name__}: OK\n")
    print(f"Tüm {len(tests)} test geçti!")

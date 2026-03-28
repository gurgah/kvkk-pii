import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from kvkk_pii import PiiDetector, LeakageAnalyzer


detector = PiiDetector()
analyzer = detector.leakage_analyzer()


def test_session_mask_restore():
    """Temel mask → restore döngüsü."""
    text = "TC: 10000000146 ve mail: ali@test.com"
    session = detector.create_session(text)
    masked = session.mask(text)

    assert "10000000146" not in masked
    assert "ali@test.com" not in masked
    assert "[TC_KIMLIK_" in masked
    assert "[EMAIL_" in masked

    restored = session.restore(masked)
    assert "10000000146" in restored
    assert "ali@test.com" in restored


def test_session_ayni_deger_ayni_placeholder():
    """Aynı değer iki kez geçerse aynı placeholder kullanılmalı."""
    text = "TC: 10000000146 ve yine TC: 10000000146"
    session = detector.create_session(text)
    masked = session.mask(text)

    placeholders = [p for p in session.mapping.keys()]
    tc_placeholders = [p for p in placeholders if "TC_KIMLIK" in p]
    assert len(tc_placeholders) == 1, "Aynı TC için tek placeholder olmalı"


def test_session_restore_partial():
    """AI response'u placeholder'ların sadece bir kısmını içeriyor olabilir."""
    text = "TC: 10000000146, mail: ali@test.com"
    session = detector.create_session(text)
    masked = session.mask(text)

    # AI sadece TC placeholder'ını kullandı
    tc_ph = [p for p in session.mapping if "TC_KIMLIK" in p][0]
    ai_response = f"{tc_ph} için kayıt bulunamadı."

    restored = session.restore(ai_response)
    assert "10000000146" in restored
    assert "ali@test.com" not in restored  # AI bunu hiç kullanmadı


def test_leakage_temiz():
    """AI orijinal değerleri döndürmediyse rapor temiz olmalı."""
    text = "TC: 10000000146"
    session = detector.create_session(text)
    masked = session.mask(text)

    tc_ph = [p for p in session.mapping if "TC_KIMLIK" in p][0]
    ai_response = f"{tc_ph} ile ilgili sonuç: Kayıt mevcut."

    report = analyzer.analyze(session, ai_response)
    assert report.safe, f"Temiz response'da sızıntı algılandı: {report.summary()}"
    assert report.risk_score == 0.0


def test_leakage_sizinti():
    """AI orijinal TC değerini response'a yazdıysa tespit edilmeli."""
    text = "TC: 10000000146"
    session = detector.create_session(text)
    session.mask(text)

    # AI kötü davrandı — orijinal değeri response'a yazdı
    ai_response = "Kişinin TC numarası 10000000146 olarak kayıtlıdır."

    report = analyzer.analyze(session, ai_response)
    assert not report.safe
    assert len(report.leaked) > 0
    assert report.risk_score > 0
    print(f"  Sızıntı tespit edildi: {report.summary()}")


def test_leakage_yeni_pii():
    """AI input'ta olmayan yeni bir PII ürettiyse (hallucination) tespit edilmeli."""
    text = "Müşteri bilgilerini kontrol et."
    session = detector.create_session(text)
    session.mask(text)

    # AI hallucinate etti — sahte bir e-posta üretdi
    ai_response = "Müşteri e-postası sahte@example.com olarak görünüyor."

    report = analyzer.analyze(session, ai_response)
    assert not report.safe
    assert len(report.new_pii) > 0
    print(f"  Hallucination tespit edildi: {report.summary()}")


def test_tam_proxy_akisi():
    """Uçtan uca: mask → (simüle AI) → leakage check → restore."""
    user_prompt = "10000000146 TC'li müşterinin hesabını göster."

    # 1. Mask
    session = detector.create_session(user_prompt)
    masked = session.mask(user_prompt)
    assert "10000000146" not in masked

    # 2. Simüle AI çağrısı (placeholder'ı aynen döndürüyor)
    tc_ph = [p for p in session.mapping if "TC_KIMLIK" in p][0]
    ai_raw_response = f"{tc_ph} numaralı hesapta 5000 TL bakiye bulunmaktadır."

    # 3. Leakage analizi (restore ÖNCE)
    report = analyzer.analyze(session, ai_raw_response)
    assert report.safe, report.summary()

    # 4. Restore
    final = session.restore(ai_raw_response)
    assert "10000000146" in final
    print(f"  Final: {final}")


if __name__ == "__main__":
    tests = [
        test_session_mask_restore,
        test_session_ayni_deger_ayni_placeholder,
        test_session_restore_partial,
        test_leakage_temiz,
        test_leakage_sizinti,
        test_leakage_yeni_pii,
        test_tam_proxy_akisi,
    ]
    for t in tests:
        t()
        print(f"  {t.__name__}: OK")
    print(f"\nTüm {len(tests)} test geçti!")

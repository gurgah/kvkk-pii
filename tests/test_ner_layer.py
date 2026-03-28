import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")

from kvkk_pii import PiiDetector


def test_ner_kisi_adi():
    d = PiiDetector(layers=["regex", "ner"], download_policy="auto")
    r = d.analyze("Ahmet Yılmaz bugün toplantıya geldi.")
    assert r.has("KISI_ADI"), f"Bulunanlar: {r.entities}"
    print(f"  Bulunan: {r.by_type('KISI_ADI')[0].text!r}")


def test_ner_konum():
    d = PiiDetector(layers=["regex", "ner"], download_policy="auto")
    r = d.analyze("Şirketimiz İstanbul Kadıköy'de bulunmaktadır.")
    assert r.has("KONUM"), f"Bulunanlar: {r.entities}"
    print(f"  Bulunan: {[e.text for e in r.by_type('KONUM')]}")


def test_ner_kurum():
    d = PiiDetector(layers=["regex", "ner"], download_policy="auto")
    r = d.analyze("Türk Telekom faturası geldi.")
    assert r.has("KURUM"), f"Bulunanlar: {r.entities}"
    print(f"  Bulunan: {r.by_type('KURUM')[0].text!r}")


def test_ner_regex_ile_beraber():
    """NER ve regex birlikte çalışmalı, overlap olmamalı."""
    d = PiiDetector(layers=["regex", "ner"], download_policy="auto")
    text = "Ahmet Yılmaz TC: 10000000146 numarasıyla kayıtlı."
    r = d.analyze(text)
    assert r.has("KISI_ADI")
    assert r.has("TC_KIMLIK")

    # Overlap kontrolü
    for i, a in enumerate(r.entities):
        for b in r.entities[i+1:]:
            assert not (a.start < b.end and b.start < a.end), \
                f"Overlap: {a} ↔ {b}"
    print(f"  Tüm entity'ler: {[(e.entity_type, e.text) for e in r.entities]}")


if __name__ == "__main__":
    tests = [test_ner_kisi_adi, test_ner_konum, test_ner_kurum, test_ner_regex_ile_beraber]
    for t in tests:
        t()
        print(f"  {t.__name__}: OK")
    print(f"\nTüm {len(tests)} NER testi geçti!")

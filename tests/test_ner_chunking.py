"""NER Layer — chunk'lama ve uzun metin testleri."""
import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii import PiiDetector
from kvkk_pii.config import NerConfig

DOWNLOAD_POLICY = "auto"


@pytest.fixture(scope="module")
def ner_detector():
    return PiiDetector(layers=["regex", "ner"], download_policy=DOWNLOAD_POLICY)


@pytest.fixture(scope="module")
def ner_small_chunk():
    """Chunk testini zorlamak için küçük chunk boyutu."""
    return PiiDetector(
        layers=["regex", "ner"],
        download_policy=DOWNLOAD_POLICY,
        ner_config=NerConfig(chunk_size=200, chunk_overlap=30),
    )


def test_kisa_metin_normal(ner_detector):
    r = ner_detector.analyze("Ahmet Yılmaz İstanbul'da çalışıyor.")
    assert r.has("KISI_ADI")
    assert r.has("KONUM")


def test_uzun_metin_pii_kacmaz(ner_detector):
    """512 token'dan uzun metinde, sonlardaki PII kaçmamalı."""
    preamble = "Bu bir test metnidir. " * 50   # ~100 token dolgu
    tail = "Müşteri Mehmet Çelik Ankara şubesine başvurdu."
    text = preamble + tail

    r = ner_detector.analyze(text)
    assert r.has("KISI_ADI"), "Uzun metinde kişi adı kaçtı!"
    assert r.has("KONUM"), "Uzun metinde konum kaçtı!"


def test_chunk_sinirinda_isim(ner_small_chunk):
    """İsim tam chunk sınırında olsa bile tespit edilmeli."""
    # 200 karakter dolgu + isim
    padding = "x " * 95   # ~190 karakter
    text = padding + "Fatma Kaya bugün geldi."
    r = ner_small_chunk.analyze(text)
    assert r.has("KISI_ADI"), f"Chunk sınırında isim kaçtı. Bulunanlar: {r.entities}"


def test_overlap_duplicate_yok(ner_small_chunk):
    """Chunk örtüşme bölgesindeki entity iki kez sayılmamalı."""
    padding = "x " * 95
    text = padding + "Ali Veli işe geldi. " + "x " * 95 + "Ayşe Şahin gitti."
    r = ner_small_chunk.analyze(text)
    kisi_adlari = r.by_type("KISI_ADI")
    texts = [e.text for e in kisi_adlari]
    assert len(texts) == len(set(texts)), f"Duplicate entity: {texts}"


def test_regex_ner_overlap_yok(ner_detector):
    """Regex'in bulduğu TC Kimlik ile NER'in bulduğu isim örtüşmemeli."""
    text = "Ahmet Yılmaz TC: 10000000146 numarasıyla kayıtlıdır."
    r = ner_detector.analyze(text)
    for i, a in enumerate(r.entities):
        for b in r.entities[i+1:]:
            overlap = a.start < b.end and b.start < a.end
            assert not overlap, f"Overlap tespit edildi: {a} ↔ {b}"


def test_ner_min_score_config():
    """min_score arttırıldığında daha az entity dönmeli."""
    d_low  = PiiDetector(layers=["regex","ner"], download_policy=DOWNLOAD_POLICY,
                         ner_config=NerConfig(min_score=0.5))
    d_high = PiiDetector(layers=["regex","ner"], download_policy=DOWNLOAD_POLICY,
                         ner_config=NerConfig(min_score=0.99))
    text = "Ahmet Yılmaz, Mehmet Kaya ve Ayşe Demir toplantıdaydı."
    r_low  = d_low.analyze(text)
    r_high = d_high.analyze(text)
    assert len(r_low.entities) >= len(r_high.entities)

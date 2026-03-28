"""
Gerçek dünya senaryoları — email, resmi yazı, banka işlemi, sağlık kaydı.
Bu testler tüm layer'ları birlikte test eder.
"""
import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii import PiiDetector

DOWNLOAD_POLICY = "auto"


@pytest.fixture(scope="module")
def d_regex():
    return PiiDetector(download_policy=DOWNLOAD_POLICY)

@pytest.fixture(scope="module")
def d_full():
    return PiiDetector(layers=["regex","ner","gliner"], download_policy=DOWNLOAD_POLICY)


# ── Senaryo 1: Resmi e-posta ──────────────────────────────────────────────────

EMAIL_TEXT = """
Konu: Hesap Bilgileri Güncelleme

Sayın Ahmet Yılmaz,

TC Kimlik Numaranız 10000000146 ile kayıtlı hesabınıza ait
bilgiler aşağıdaki gibi güncellenmiştir:

  E-posta : ahmetyilmaz@ornek.com.tr
  Telefon : 0532 999 88 77
  IBAN    : TR330006100519786457841326

Sorularınız için 0212 444 00 00 numaralı hattımızı arayabilirsiniz.
"""

def test_email_tc_bulunur(d_regex):
    r = d_regex.analyze(EMAIL_TEXT)
    assert r.has("TC_KIMLIK"), "TC bulunamadı"

def test_email_iban_bulunur(d_regex):
    assert d_regex.analyze(EMAIL_TEXT).has("IBAN_TR")

def test_email_mobil_bulunur(d_regex):
    assert d_regex.analyze(EMAIL_TEXT).has("TELEFON_TR")

def test_email_sabit_hat_bulunur(d_regex):
    phones = d_regex.analyze(EMAIL_TEXT).by_type("TELEFON_TR")
    assert len(phones) == 2, f"Beklenen 2 telefon, bulunan: {[p.text for p in phones]}"

def test_email_eposta_bulunur(d_regex):
    assert d_regex.analyze(EMAIL_TEXT).has("EMAIL")

def test_email_kisi_ner(d_full):
    r = d_full.analyze(EMAIL_TEXT)
    assert r.has("KISI_ADI"), f"Kişi adı bulunamadı. Bulunanlar: {r.entities}"

def test_email_anonymize(d_regex):
    anon = d_regex.anonymize(EMAIL_TEXT)
    assert "10000000146" not in anon
    assert "TR330006100519786457841326" not in anon
    assert "ahmetyilmaz@ornek.com.tr" not in anon


# ── Senaryo 2: Banka işlem kaydı ─────────────────────────────────────────────

BANKA_TEXT = """
İşlem No: 2024031500001
Tarih    : 15.03.2024 14:32:15
Gönderen : Ahmet Yılmaz (TC: 10000000146)
IBAN     : TR330006100519786457841326
Alıcı    : Fatma Kaya
Tutar    : 5.000 TL
Açıklama : Kira ödemesi
"""

def test_banka_tc(d_regex):
    assert d_regex.analyze(BANKA_TEXT).has("TC_KIMLIK")

def test_banka_iban(d_regex):
    assert d_regex.analyze(BANKA_TEXT).has("IBAN_TR")

def test_banka_iki_kisi_ner(d_full):
    r = d_full.analyze(BANKA_TEXT)
    kisiler = r.by_type("KISI_ADI")
    names = [e.text for e in kisiler]
    assert "Ahmet Yılmaz" in names, f"Bulunanlar: {names}"


# ── Senaryo 3: Sağlık kaydı (KVKK Madde 6) ──────────────────────────────────

SAGLIK_TEXT = """
Hasta Adı  : Mehmet Çelik
TC         : 20000000046
SGK No     : SGK No: 987654321
Tanı       : Tip 2 Diyabet, kan şekeri 250 mg/dL
Dini Görüş : Hasta oruç tuttuğunu belirtmiştir.
İlaç       : Metformin 1000mg
"""

def test_saglik_tc(d_regex):
    assert d_regex.analyze(SAGLIK_TEXT).has("TC_KIMLIK")

def test_saglik_sgk(d_regex):
    assert d_regex.analyze(SAGLIK_TEXT).has("SGK_NO")

def test_saglik_kisi_ner(d_full):
    r = d_full.analyze(SAGLIK_TEXT)
    assert r.has("KISI_ADI")

def test_saglik_kvkk_md6_gliner(d_full):
    r = d_full.analyze(SAGLIK_TEXT)
    kvkk_types = {"SAGLIK_VERISI", "DINI_INANC"}
    found = {e.entity_type for e in r.entities}
    assert kvkk_types & found, f"KVKK Madde 6 entity bulunamadı. Bulunanlar: {found}"


# ── Senaryo 4: Boşluklu/tireli yazım (kullanıcı hataları) ───────────────────

def test_tc_spaced(d_regex):
    r = d_regex.analyze("TC: 100 000 001 46")
    assert r.has("TC_KIMLIK"), "Boşluklu TC bulunamadı"

def test_tc_dashed(d_regex):
    r = d_regex.analyze("TC kimliğim: 100-000-001-46")
    assert r.has("TC_KIMLIK"), "Tireli TC bulunamadı"

def test_telefon_parantezli(d_regex):
    assert d_regex.analyze("0(532) 999 88 77").has("TELEFON_TR")


# ── Senaryo 5: İki yönlü proxy (email yazma) ─────────────────────────────────

def test_two_way_email_yazma(d_full):
    def sahte_gpt(masked: str) -> str:
        # Placeholder'ları aynen kullanan sahte AI
        import re
        placeholders = re.findall(r'\[[A-Z_]+_[a-z0-9]{3}\]', masked)
        ph_kisi = next((p for p in placeholders if "KISI" in p), "[KİŞİ]")
        ph_tc   = next((p for p in placeholders if "TC" in p), "[TC]")
        return f"Sayın {ph_kisi}, TC numaranız {ph_tc} ile hesabınız onaylandı."

    result = d_full.two_way(
        prompt="Ali Veli (TC: 10000000146) için onay emaili yaz.",
        call_fn=sahte_gpt,
    )
    assert result.safe, result.report.summary()
    assert "Ali Veli" in result.output
    assert "10000000146" in result.output


# ── Senaryo 6: Karışık dil (Türkçe + İngilizce) ──────────────────────────────

MIXED_TEXT = """
Dear Ahmet Yılmaz,
Your TC ID: 10000000146 has been verified.
Please contact us at ahmet@example.com or call +90 532 123 45 67.
"""

def test_karisik_dil_tc(d_regex):
    assert d_regex.analyze(MIXED_TEXT).has("TC_KIMLIK")

def test_karisik_dil_email(d_regex):
    assert d_regex.analyze(MIXED_TEXT).has("EMAIL")

def test_karisik_dil_telefon(d_regex):
    assert d_regex.analyze(MIXED_TEXT).has("TELEFON_TR")

def test_karisik_dil_kisi_ner(d_full):
    assert d_full.analyze(MIXED_TEXT).has("KISI_ADI")

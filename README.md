# kvkk-pii

**Python ile KVKK uyumlu kişisel veri tespiti ve anonimleştirme kütüphanesi.**

Türkçe metinlerde TC kimlik numarası, IBAN, telefon, e-posta ve daha fazlasını tespit edin. Yapay zekâya göndermeden önce verileri maskeleyin. KVKK Madde 6 özel nitelikli kategorileri (sağlık, din, biyometri) otomatik işaretleyin. Tüm işlemler yerel makinede — hiçbir veri dışarı çıkmaz.

```python
from kvkk_pii import PiiDetector

detector = PiiDetector()
sonuc = detector.analyze("Ali Veli, TC: 10000000146, tel: 0532 123 45 67")

for e in sonuc.entities:
    print(e)
# PiiEntity(type='TC_KIMLIK', text='10000000146', score=1.00, layer='regex')
# PiiEntity(type='TELEFON_TR', text='0532 123 45 67', score=1.00, layer='regex')
```

---

## Neden kvkk-pii?

- **KVKK odaklı** — TC Kimlik, VKN, IBAN, SGK, plaka ve Madde 6 özel kategoriler
- **Tamamen yerel** — model cihaza indirilir, veri hiçbir sunucuya gitmez
- **3 katmanlı tespit** — Regex → XLM-RoBERTa NER → GLiNER (sıfır atışlı)
- **Yapay zekâ proxy** — ChatGPT/Claude'a göndermeden önce maskele, sonra geri yükle
- **Uyum raporu** — tespit edilen verileri KVKK maddelerine göre sınıflandır
- **Kolay entegrasyon** — FastAPI, Django, Celery ile uyumlu; async desteği var
- **Özelleştirilebilir** — kendi recognizer'ını yaz, eşik değerlerini ayarla

---

## Kurulum

```bash
# Sadece regex katmanı (bağımlılık yok)
pip install kvkk-pii

# + NER katmanı — Türkçe isim/yer/kurum tespiti (~450 MB)
pip install kvkk-pii[ner]

# + GLiNER — KVKK Madde 6 özel kategoriler (~180 MB)
pip install kvkk-pii[full]
```

Modeller ilk kullanımda HuggingFace'den indirilir ve `~/.cache/huggingface/hub` konumuna kaydedilir.

---

## Kullanım Senaryoları

### 1. Log Anonimleştirme

Uygulama loglarında kişisel veri varsa KVKK ihlali doğuyor. Logları kaydetmeden önce otomatik maskeleyin.

```python
from kvkk_pii import PiiDetector

detector = PiiDetector()

log_satiri = "Kullanıcı 532 123 45 67 numaralı telefonla giriş yaptı, IP: 192.168.1.1"
temiz_log = detector.anonymize(log_satiri)
# → "Kullanıcı [TELEFON_TR] numaralı telefonla giriş yaptı, IP: [IP_ADRESI]"
```

---

### 2. ChatGPT / Claude'a Güvenli Veri Gönderme

Müşteri verisini yapay zekâya göndermeden önce maskeleyin, yanıtı geri yükleyin. Veri hiçbir zaman OpenAI'a ulaşmaz.

```python
import openai
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])

sonuc = detector.two_way(
    prompt="Ahmet Yılmaz'ın (TC: 10000000146) sigorta dosyasını özetle.",
    call_fn=lambda maskeli: openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": maskeli}]
    ).choices[0].message.content,
    on_leak="warn",  # sızıntı varsa uyar
)

print(sonuc.output)         # orijinal isim/TC geri yüklenmiş yanıt
print(sonuc.report.safe)    # True → sızıntı yok
```

---

### 3. E-posta ve Belge Özetleme

Şirket içi e-postalar veya resmi belgeler AI'a gitmeden önce temizlenir, özet gelince orijinal veriler geri eklenir.

```python
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])

eposta = """
Sayın Fatma Kaya,
IBAN'ınız TR33 0006 1005 1978 6457 8413 26 üzerinden
15.000 TL ödeme yapılacaktır.
"""

session = detector.create_session(eposta)
maskeli = session.mask()
# → "Sayın [KISI_ADI_x3k], IBAN'ınız [IBAN_TR_b9f] üzerinden ..."

ai_ozet = yapay_zeka_cagri(maskeli)
geri_yuklenmis = session.restore(ai_ozet)
```

---

### 4. Form ve Kullanıcı Girişi Tarama

Kayıt formlarında, müşteri yorumlarında veya destek taleplerinde kişisel veri kontrolü yapın.

```python
detector = PiiDetector()

yorum = "Merhaba, TC'm 10000000146, lütfen iade işlemi yapın."
sonuc = detector.analyze(yorum)

if sonuc.has("TC_KIMLIK"):
    # Formdan TC almayı engelle veya maskele
    temiz = detector.anonymize(yorum)
```

---

### 5. Veritabanı / CSV Temizleme

Eski veritabanlarında veya içe aktarılan CSV dosyalarında kişisel veri taraması yapın.

```python
import csv
from kvkk_pii import PiiDetector

detector = PiiDetector()

with open("musteriler.csv") as f:
    satirlar = list(csv.reader(f))

for satir in satirlar:
    metin = " ".join(satir)
    sonuc = detector.analyze(metin)
    if sonuc.entities:
        print(f"KVKK verisi bulundu: {[e.entity_type for e in sonuc.entities]}")
```

---

### 6. KVKK Uyum Raporu

İşlediğiniz metnin KVKK'ya göre risk seviyesini ve ilgili maddeleri otomatik raporlayın.

```python
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner", "gliner"])

metin = "Hasta diyabet tedavisi görüyor. TC: 10000000146, tel: 0532 123 45 67"
rapor = detector.compliance_report(metin)

print(rapor.summary())
# KVKK Uyum Raporu — 3 veri, genel risk: KRİTİK
# KVKK Madde 6 (Özel Nitelikli Veri) tespit edildi!
#
#   [KRİTİK] SAGLIK_VERISI x 1
#     Dayanak: KVKK Madde 6 — Özel Nitelikli Kişisel Veri
#     Öneri  : Açık rıza zorunlu. Yetkili kurum olmadan işlenemez.
#   [YÜKSEK] TC_KIMLIK x 1
#     ...
```

---

### 7. FastAPI ile Servis Olarak Kullanma

```python
from fastapi import FastAPI
from kvkk_pii import AsyncPiiDetector

app = FastAPI()
detector = AsyncPiiDetector(layers=["regex", "ner"])

@app.post("/tarama")
async def tarama(metin: str):
    sonuc = await detector.analyze(metin)
    return {
        "entity_sayisi": len(sonuc.entities),
        "tipler": [e.entity_type for e in sonuc.entities],
        "anonim": sonuc.anonymize(),
    }
```

---

### 8. PII Sızıntısı Tespiti

Yapay zekânın yanıtında orijinal kişisel veri sızdı mı? Otomatik kontrol edin.

```python
from kvkk_pii import PiiDetector, LeakageAnalyzer

detector = PiiDetector(layers=["regex", "ner"])
session = detector.create_session("Ali Veli, 0532 123 45 67 numaralı müşteri.")
maskeli = session.mask()

ai_yaniti = yapay_zeka_cagri(maskeli)

analyzer = LeakageAnalyzer(detector)
rapor = analyzer.analyze(session, ai_yaniti)

print(rapor.safe)       # False → sızıntı var
print(rapor.summary())  # hangi veriler sızdı
```

---

## Katman Mimarisi

| Katman | Yöntem | Model | Hız | Ne tespit eder |
|--------|--------|-------|-----|----------------|
| 1 | Regex + checksum | — | <1ms | TC Kimlik, IBAN, VKN, telefon, plaka, e-posta, pasaport |
| 2 | NER | `akdeniz27/xlm-roberta-base-turkish-ner` | ~30ms | Kişi adı, konum, kurum |
| 3 | Sıfır atışlı | `urchade/gliner_multi-v2.1` | ~80ms | KVKK Madde 6 özel kategoriler |

Her katman, bir öncekinin bulduğu span'leri atlar — aynı veri iki kez işaretlenmez.

---

## Tespit Edilen Veri Türleri

### Katman 1 — Regex

| Tür | Açıklama | Doğrulama |
|-----|----------|-----------|
| `TC_KIMLIK` | 11 haneli TC kimlik numarası | Checksum |
| `VKN` | 10 haneli vergi kimlik numarası | Checksum |
| `IBAN_TR` | IBAN (tüm ülke kodları) | Mod97 |
| `KREDI_KARTI` | Kredi kartı numarası | Luhn |
| `TELEFON_TR` | Türk telefon numaraları | — |
| `EMAIL` | E-posta adresi | — |
| `IP_ADRESI` | IPv4 adresi | — |
| `PLAKA_TR` | Türk plaka numarası | — |
| `PASAPORT_TR` | Türk pasaport numarası | — |
| `SGK_NO` | SGK işyeri numarası | — |
| `ADRES` | Sokak adresi | — |
| `TARIH` | Tarih | — |
| `KISI_ADI` | Ünvan bazlı kişi adı | — |

### Katman 2 — NER

| Tür | Açıklama |
|-----|----------|
| `KISI_ADI` | Kişi adı (model bazlı) |
| `KONUM` | Şehir, ilçe, ülke |
| `KURUM` | Şirket, kurum adı |

### Katman 3 — GLiNER (KVKK Madde 6)

| Tür | KVKK Karşılığı |
|-----|----------------|
| `SAGLIK_VERISI` | Sağlık verisi |
| `DINI_INANC` | Din, mezhep bilgisi |
| `SIYASI_GORUS` | Siyasi görüş |
| `SENDIKA_UYELIGII` | Sendika üyeliği |
| `BIYOMETRIK_VERI` | Biyometrik / genetik veri |

---

## Hazır Preset'ler

```python
from kvkk_pii import presets

detector = presets.turkish()       # KVKK — regex + NER (TR) + GLiNER
detector = presets.german()        # DSGVO — regex (DE) + GLiNER
detector = presets.french()        # RGPD — regex (FR) + GLiNER
detector = presets.multilingual()  # TR + DE + FR birlikte
```

---

## Özel Recognizer Ekleme

```python
from kvkk_pii import BaseRecognizer, PiiEntity, PiiDetector
from kvkk_pii.layers.regex_layer import DEFAULT_RECOGNIZERS

class SicilNoRecognizer(BaseRecognizer):
    entity_type = "SICIL_NO"

    def find(self, text: str) -> list[PiiEntity]:
        import re
        return [
            self._entity(m.group(), m.start(), m.end(), score=1.0)
            for m in re.finditer(r"\bSCL-\d{6}\b", text)
        ]

detector = PiiDetector(recognizers=DEFAULT_RECOGNIZERS + [SicilNoRecognizer()])
```

---

## Komut Satırı (CLI)

```bash
# Metin tara
kvkk-pii scan "Ali Veli TC: 10000000146"

# Dosya tara
kvkk-pii scan belge.txt

# Pipe ile kullan
cat belge.txt | kvkk-pii scan

# NER katmanıyla tara
kvkk-pii scan --layer ner "Ahmet Yılmaz İstanbul'da"

# JSON çıktı
kvkk-pii scan --format json "TC: 10000000146"

# Anonimleştir
kvkk-pii anonymize "Ali Veli TC: 10000000146"
# → "Ali Veli TC: [TC_KIMLIK]"
```

---

## Yapılandırma

```python
from kvkk_pii import PiiDetector
from kvkk_pii.config import NerConfig, GlinerConfig

detector = PiiDetector(
    layers=["regex", "ner", "gliner"],
    download_policy="auto",    # "confirm" (varsayılan) | "auto" | "never"
    ner_config=NerConfig(
        min_score=0.85,        # yüksek = daha az yanlış pozitif
        chunk_size=400,        # uzun metinler için chunk boyutu
    ),
    gliner_config=GlinerConfig(
        threshold=0.5,
    ),
)
```

---

## Gereksinimler

- Python 3.10+
- `pip install kvkk-pii` → bağımlılık yok
- `pip install kvkk-pii[ner]` → `transformers`, `torch`, `huggingface-hub`
- `pip install kvkk-pii[full]` → yukarıdaki + `gliner`
- `pip install kvkk-pii[server]` → yukarıdaki + `fastapi`, `uvicorn`

---

## Lisans

MIT

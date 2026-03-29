# kvkk-pii

[![PyPI](https://img.shields.io/pypi/v/kvkk-pii)](https://pypi.org/project/kvkk-pii/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/kvkk-pii/)
[![Lisans](https://img.shields.io/pypi/l/kvkk-pii)](LICENSE)

**Türkçe metinlerde kişisel veri tespiti, maskeleme ve KVKK uyum kontrolü — tek kütüphane.**

---

Şirketinizde yapay zeka kullanılıyor. Destek ekibi müşteri mesajlarını ChatGPT'ye yapıştırıyor. Geliştiriciler API'ye tam metni gönderiyor. Muhasebe e-postaları özetletiliyor.

Bu metinlerin içinde ne var?

**TC kimlik numarası. IBAN. Telefon numarası. Hasta bilgisi. Kişi adları.**

Bunların tamamı — yani PII (Personally Identifiable Information / kişisel tanımlanabilir bilgi) — o anda OpenAI, Google veya başka bir şirketin sunucusuna gidiyor. Çoğu zaman kimse farkında bile değil.

Bu bir KVKK ihlali. Ve son kullanıcı değil, veriyi işleyen şirket sorumlu.

---

### İki yönlü koruma — veri hiç dışarı çıkmaz

`kvkk-pii` yapay zeka entegrasyonlarında **iki yönlü çalışır:**

```
  Kullanıcı metni
        │
        ▼
┌───────────────────┐
│     kvkk-pii      │
│  ① Veri tespiti   │  TC, IBAN, isim, telefon...
│  ② Maskeleme      │  → [TC_KIMLIK_a3f], [KISI_ADI_x7k]
└────────┬──────────┘
         │  maskeli metin (kişisel veri yok)
         ▼
  ┌─────────────┐
  │  ChatGPT /  │
  │  Claude /   │
  │   LLM API   │
  └──────┬──────┘
         │  AI yanıtı (token'larla)
         ▼
┌───────────────────┐
│     kvkk-pii      │
│  ③ Sızıntı        │  gerçek veri sızdı mı?
│     kontrolü      │
│  ④ Geri yükleme   │  [TC_KIMLIK_a3f] → 10000000146
└────────┬──────────┘
         │
         ▼
  Kullanıcıya yanıt
  (orijinal verilerle)
```

Yapay zeka modeli hiçbir zaman gerçek kişisel veriyi görmez.

```python
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])

sonuc = detector.two_way(
    prompt="Ahmet Yılmaz (TC: 10000000146) iade talebini ilet.",
    call_fn=lambda maskeli: openai_cagri(maskeli),
)

print(sonuc.output)         # AI yanıtı — orijinal isim ve TC geri yüklendi
print(sonuc.report.safe)    # True → hiçbir veri sızmadı
```

---

### Kişisel veri sızıntısı (PII leakage) nedir?

Yapay zeka modeline maskelenmiş veri gönderdiniz — ama model yanıtında yine de gerçek kişisel veriyi kullandı. Ya da prompt içindeki kişisel veriyi hiç fark etmeden geçirdiniz ve model bunu üçüncü bir içeriğe dahil etti. Buna **kişisel veri sızıntısı** (PII leakage) denir.

`kvkk-pii` AI yanıtını otomatik tarar: maskelenen veriler geri döndü mü, yeni kişisel veri ortaya çıktı mı, risk var mı?

```python
print(sonuc.report.leaked)    # sızan veri listesi
print(sonuc.report.new_pii)   # AI'ın kendi ürettiği kişisel veri
print(sonuc.report.risk_score) # 0.0 güvenli — 1.0 kritik
```

---

### KVKK uyum (compliance) raporu

Sadece maskeleme değil — işlenen verinin **hangi KVKK maddesini ilgilendirdiğini**, risk seviyesini ve yasal öneriyi de raporlar.

```python
rapor = detector.compliance_report(metin)
print(rapor.summary())
# KVKK Uyum Raporu — genel risk: KRİTİK
# KVKK Madde 6 (Özel Nitelikli Veri) tespit edildi!
#   [KRİTİK] SAGLIK_VERISI — Açık rıza zorunlu.
```

---

`pip install kvkk-pii`

---

## Katmanlar — ne seçmeli?

Üç katman bağımsız veya birlikte kullanılabilir. **Varsayılan: sadece regex.**

| Katman | Seçim | Model | Boyut | Ne tespit eder | Ne zaman gerekli |
|--------|-------|-------|-------|----------------|-----------------|
| **Regex** | varsayılan | — | 0 MB | TC, IBAN, VKN, telefon, e-posta, plaka... | Her zaman — yapılandırılmış veri |
| **NER** | `"ner"` | XLM-RoBERTa (TR) | ~450 MB | Kişi adı, kurum, konum | E-posta, chat, belge — serbest metin |
| **GLiNER** | `"gliner"` | GLiNER multi | ~180 MB | Sağlık, din, siyasi görüş, sendika, biyometri | KVKK Madde 6 uyumu |

```python
PiiDetector()                                        # sadece regex (varsayılan)
PiiDetector(layers=["regex", "ner"])                 # + isim/kurum/konum
PiiDetector(layers=["regex", "gliner"])              # + Madde 6, NER olmadan
PiiDetector(layers=["regex", "ner", "gliner"])       # tam sistem
```

**NER mi GLiNER mi?** İkisi farklı şey yapar — birbirinin alternatifi değil. NER Türkçe isim/kurum/konumda %94.92 F1 ile çalışır, GLiNER ise NER'in göremediği KVKK Madde 6 kategorilerini (sağlık, din, biyometri) yakalar. Sadece hafif bir kurulum istiyorsanız `["regex", "gliner"]` da geçerli — GLiNER isim de yakalayabilir ama Türkçe'de NER kadar başarılı değildir.

**Conflict olur mu? Hayır.** Her katman, önceki katmanların bulduğu span'leri atlar — aynı metin parçası hiçbir zaman iki kez işaretlenmez:

```
Regex  → "10000000146" buldu  [0-11]
NER    → [0-11] zaten dolu, atla
GLiNER → [0-11] zaten dolu, atla
```

---

## Hangi kurulum bana göre?

| Durum | Kurulum | Kod |
|-------|---------|-----|
| Form/veritabanı tarama, log temizleme | `pip install kvkk-pii` | `PiiDetector()` |
| E-posta, chat, müşteri mesajı | `pip install kvkk-pii[ner]` | `PiiDetector(layers=["regex", "ner"])` |
| Sağlık, HR, hukuk belgesi (Madde 6) | `pip install kvkk-pii[full]` | `PiiDetector(layers=["regex", "ner", "gliner"])` |
| Hafif kurulum + Madde 6 (NER olmadan) | `pip install kvkk-pii[full]` | `PiiDetector(layers=["regex", "gliner"])` |
| Çok dilli metin (TR+EN+DE) | `pip install kvkk-pii[full]` | `presets.multilingual()` |

---

## Kurulum

```bash
pip install kvkk-pii          # sadece regex (bağımlılık yok)
pip install kvkk-pii[ner]     # + Türkçe NER (~450 MB)
pip install kvkk-pii[full]    # + NER + GLiNER (~630 MB toplam)
```

---

## Gerçek Senaryolar

### Senaryo 1 — Destek ekibi müşteri mesajını AI ile yanıtlıyor

**Problem:** Müşteri hizmetleri ekibi gelen mesajları ChatGPT'ye yapıştırarak yanıt taslağı oluşturuyor. Mesajların içinde isim, telefon, TC kimlik numarası var. Bunların tamamı OpenAI sunucularına gidiyor — şirket habersiz.

**Çözüm:** Mesaj AI'ya gitmeden önce kişisel veriler maskelenir, AI maskeli metinle çalışır, yanıt kullanıcıya geri verilmeden orijinal veriler restore edilir.

```python
detector = PiiDetector(layers=["regex", "ner"])

mesaj = "Ahmet Yılmaz, 0532 123 45 67, siparişim nerede?"
session = detector.create_session(mesaj)
maskeli = session.mask()
# → "[KISI_ADI_x3k], [TELEFON_TR_b7f], siparişim nerede?"

ai_yaniti = openai_cagri(maskeli)
# AI yanıtlar: "Merhaba [KISI_ADI_x3k], [TELEFON_TR_b7f] numaranıza
#               SMS gönderdik, siparişiniz kargoya verildi."

temiz_yanit = session.restore(ai_yaniti)
# → "Merhaba Ahmet Yılmaz, 0532 123 45 67 numaranıza
#    SMS gönderdik, siparişiniz kargoya verildi."
```

---

### Senaryo 2 — Finansal e-posta özetleme

**Problem:** Muhasebe ve hukuk ekipleri IBAN, kişi adı ve tutar içeren e-postaları AI ile özetletiyor. Bu e-postalar şirket içi gizli finansal veri içeriyor — üçüncü taraf bir AI'a gönderilmesi hem KVKK hem ticari sır ihlali.

**Çözüm:** E-posta AI'ya gitmeden önce otomatik maskelenir. Özet gelince hassas veriler geri yüklenir. Sızıntı olursa işlem durdurulur.

```python
eposta = """
Sayın Fatma Kaya,
TR33 0006 1005 1978 6457 8413 26 no'lu hesabınıza
42.500 TL ödeme yapılacaktır. İmzalı teyit bekliyoruz.
"""

sonuc = detector.two_way(
    prompt=eposta,
    call_fn=lambda m: ai_ozet(m),
    on_leak="raise",  # sızıntı varsa hata fırlat
)

print(sonuc.output)
# → "Fatma Kaya'nın hesabına 42.500 TL ödeme yapılacak, teyit bekleniyor."
#   (IBAN ve isim AI'ya hiç gitmedi, özette geri yüklendi)
```

---

### Senaryo 3 — Sağlık verisi tespiti (KVKK Madde 6)

**Problem:** Bir sağlık uygulaması hasta notlarını veritabanına yazıyor. Bu notlarda tanı bilgisi, din, sendika üyeliği gibi KVKK Madde 6 kapsamında "özel nitelikli" veriler olabilir. Bunlar yanlışlıkla loglara düşüyor ya da yetkisiz kişilerle paylaşılıyor.

**Çözüm:** Her kayıt öncesi metin taranır, hangi KVKK maddelerini tetiklediği ve risk seviyesi otomatik raporlanır.

```python
detector = PiiDetector(layers=["regex", "ner", "gliner"])

# Gerçekçi bir hasta taburcu notu
hasta_notu = """
Hasta 52 yaşında erkek, tip 2 diyabet ve kronik böbrek yetmezliği tanıları mevcut.
Metformin 1000mg 2x1 kullanıyor. Dini gerekçeyle kan transfüzyonunu reddetti,
alternatif tedavi protokolü uygulandı.
"""

rapor = detector.compliance_report(hasta_notu)

print(rapor.summary())
# KVKK Uyum Raporu — genel risk: KRİTİK
# KVKK Madde 6 (Özel Nitelikli Veri) tespit edildi!
#   [KRİTİK] SAGLIK_VERISI — Açık rıza zorunlu. Yetkili kurum olmadan işlenemez.
#   [KRİTİK] DINI_INANC   — Kural olarak işlenemez.

print(rapor.has_madde6)  # True
```

---

### Senaryo 4 — Log anonimleştirme

**Problem:** Uygulama logları hata ayıklama için değerli ama içinde kullanıcı telefonu, e-postası, IP adresi var. Bu loglar Datadog, Elastic veya S3'e gönderiliyor — yani kişisel veri üçüncü taraflara akıyor. KVKK bu durumu açıkça ihlal sayar.

**Çözüm:** Logging katmanına tek satır filtre eklenir. Tüm loglar diske veya servise gitmeden önce otomatik temizlenir.

```python
import logging
from kvkk_pii import PiiDetector

detector = PiiDetector()

class KvkkLogFilter(logging.Filter):
    def filter(self, record):
        record.msg = detector.anonymize(str(record.msg))
        return True

logging.getLogger().addFilter(KvkkLogFilter())

logging.info("Kullanıcı 0532 123 45 67 ile giriş yaptı")
# → "Kullanıcı [TELEFON_TR] ile giriş yaptı"

logging.warning("Hata: ali@example.com, IP: 192.168.1.1")
# → "Hata: [EMAIL], IP: [IP_ADRESI]"
```

---

### Senaryo 5 — FastAPI ile kişisel veri tarama servisi

**Problem:** Büyük bir ekipte her geliştiricinin kütüphaneyi ayrı ayrı entegre etmesi zor. Merkezi bir tarama servisi olsa tüm mikroservisler oraya istek atabilir.

**Çözüm:** `kvkk-pii`'yi tek bir FastAPI servisi olarak ayağa kaldır, diğer servisler REST ile çağırsın.

```python
from fastapi import FastAPI
from kvkk_pii import AsyncPiiDetector

app = FastAPI()
detector = AsyncPiiDetector(layers=["regex", "ner"])

@app.post("/tarama")
async def tarama(metin: str):
    sonuc = await detector.analyze(metin)
    return {
        "pii_var": bool(sonuc.entities),
        "tipler": [e.entity_type for e in sonuc.entities],
        "anonim": sonuc.anonymize(),
    }

@app.post("/anonim")
async def anonim(metin: str):
    return {"sonuc": await detector.anonymize(metin)}
```

---

### Senaryo 6 — CI/CD pipeline'ında KVKK uyum kontrolü

**Problem:** Staging veya üretim ortamına deploy edilecek kod, kullanıcı verisi işleyen metin sabitleri veya test fixture'ları içerebilir. Bunlar fark edilmeden repoya giriyor.

**Çözüm:** KVKK uyum raporunu CI adımına ekle. `has_madde6` veya `risk_level == "KRİTİK"` içeren commit/deploy'u otomatik olarak durdur.

```python
# scripts/kvkk_check.py — CI adımı olarak çalıştırılır
import sys
import glob
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])
failed = False

# Test fixture ve seed dosyalarını tara
for path in glob.glob("tests/fixtures/**/*.txt", recursive=True):
    text = open(path).read()
    rapor = detector.compliance_report(text)

    if rapor.risk_level in ("YÜKSEK", "KRİTİK"):
        print(f"[KVKK] {path}: {rapor.summary()}", file=sys.stderr)
        failed = True

sys.exit(1 if failed else 0)
```

GitHub Actions entegrasyonu:

```yaml
# .github/workflows/kvkk.yml
name: KVKK Uyum Kontrolü

on: [push, pull_request]

jobs:
  kvkk-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install kvkk-pii[ner]
      - run: python scripts/kvkk_check.py
```

Gerçek TC kimlik, IBAN veya sağlık verisi içeren bir dosya commit'e girerse pipeline derleme aşamasında durur — production'a ulaşmadan önce.

---

## Tespit Edilen Veri Türleri

### Katman 1 — Regex + Checksum (bağımlılık yok)

| Tür | Açıklama | Doğrulama |
|-----|----------|-----------|
| `TC_KIMLIK` | TC kimlik numarası (11 hane) | Checksum |
| `VKN` | Vergi kimlik numarası (10 hane) | Checksum |
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

### Katman 2 — NER (`pip install kvkk-pii[ner]`)

Model: `akdeniz27/xlm-roberta-base-turkish-ner` — %94.92 F1

| Tür | Açıklama |
|-----|----------|
| `KISI_ADI` | Kişi adı |
| `KONUM` | Şehir, ilçe, ülke |
| `KURUM` | Şirket, kurum adı |

### Katman 3 — KVKK Madde 6 (`pip install kvkk-pii[full]`)

Model: `urchade/gliner_multi-v2.1` — sıfır atışlı, 100+ dil

| Tür | Açıklama |
|-----|----------|
| `SAGLIK_VERISI` | Sağlık ve tıbbi veri |
| `DINI_INANC` | Din, mezhep bilgisi |
| `SIYASI_GORUS` | Siyasi görüş |
| `SENDIKA_UYELIGII` | Sendika üyeliği |
| `BIYOMETRIK_VERI` | Biyometrik / genetik veri |

---

## Diğer Özellikler

### Hazır preset'ler

```python
from kvkk_pii import presets

detector = presets.turkish()       # KVKK — tam Türkçe destek
detector = presets.german()        # DSGVO
detector = presets.french()        # RGPD
detector = presets.multilingual()  # TR + DE + FR
```

### Komut satırı

```bash
kvkk-pii scan "Ali Veli TC: 10000000146"
kvkk-pii scan --layer ner belge.txt
kvkk-pii scan --format json "metin"
kvkk-pii anonymize "Ali Veli TC: 10000000146"
cat log.txt | kvkk-pii anonymize
```

### NER modelini değiştirme

Varsayılan NER modeli `akdeniz27/xlm-roberta-base-turkish-ner` — HuggingFace'ten otomatik indirilir. İstediğiniz modelle değiştirebilirsiniz:

```python
from kvkk_pii import PiiDetector
from kvkk_pii.config import NerConfig

# Farklı bir HuggingFace NER modeli
detector = PiiDetector(
    layers=["regex", "ner"],
    ner_config=NerConfig(
        model_id="Jean-Baptiste/roberta-large-ner-english",
        model_size_mb=1400,
        min_score=0.85,
    )
)

# Yerel diske önceden indirilmiş model (offline ortam)
detector = PiiDetector(
    layers=["regex", "ner"],
    ner_config=NerConfig(
        model_id="/opt/models/turkish-ner",  # local path
    ),
    download_policy="never",  # indirme yok, hazır model kullan
)
```

Model cache'i: `~/.cache/huggingface/hub` — `HF_HOME` env variable ile değiştirilebilir.

---

### Maskeleme token formatını değiştirme

Varsayılan format `[TC_KIMLIK_a3f]` şeklindedir. JSON, SQL veya XML içinde köşeli parantez sorun çıkarıyorsa formatı özelleştirebilirsiniz:

```python
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])

metin = "Ahmet Yılmaz, TC: 10000000146, tel: 0532 123 45 67"

# Varsayılan format — [TC_KIMLIK_a3f]
session = detector.create_session(metin)

# JSON/SQL için güvenli — __TC_KIMLIK_a3f__
session = detector.create_session(metin, token_format="__{type}_{id}__")

# XML için güvenli — PII_TC_KIMLIK_a3f
session = detector.create_session(metin, token_format="PII_{type}_{id}")

# Özel format — <<TC_KIMLIK_a3f>>
session = detector.create_session(metin, token_format="<<{type}_{id}>>")

masked = session.mask()
# → "__KISI_ADI_x7k__, TC: __TC_KIMLIK_a3f__, tel: __TELEFON_TR_b2c__"

# two_way() ile de kullanılabilir
sonuc = detector.two_way(
    prompt=metin,
    call_fn=lambda m: ai_yanit(m),
    token_format="__{type}_{id}__",
)
```

`{type}` entity tipini, `{id}` 3 karakterli benzersiz kimliği temsil eder. Restore her zaman çalışır — format ne olursa olsun.

---

### Recognizer'ları devre dışı bırakma

Belirli tipleri tespitten çıkarmak için `disable` parametresi:

```python
# EMAIL ve IP tespitini kapat
detector = PiiDetector(disable=["EMAIL", "IP_ADRESI"])
result = detector.analyze("ali@ornek.com, 192.168.1.1, TC: 10000000146")
# Sadece TC_KIMLIK bulunur
```

### Özel recognizer — before / after

Varsayılan recognizer listesini koruyarak önüne (`before`) veya arkasına (`after`) özel recognizer ekle:

```python
from kvkk_pii import BaseRecognizer, PiiEntity, PiiDetector

class SicilNoRecognizer(BaseRecognizer):
    entity_type = "SICIL_NO"

    def find(self, text: str) -> list[PiiEntity]:
        import re
        return [
            self._entity(m.group(), m.start(), m.end(), score=1.0)
            for m in re.finditer(r"\bSCL-\d{6}\b", text)
        ]

# Varsayılan recognizer'ların önünde çalışır
detector = PiiDetector(before=[SicilNoRecognizer()])

# Varsayılan recognizer'ların arkasında çalışır
detector = PiiDetector(after=[SicilNoRecognizer()])

# disable + after birlikte
detector = PiiDetector(disable=["EMAIL"], after=[SicilNoRecognizer()])
```

> `recognizers=` parametresi varsayılan listeyi tamamen değiştirir.
> `before`/`after` ise varsayılan listeyi koruyarak etrafına ekler.

---

## Gereksinimler

- Python 3.10+
- Temel kurulum: sıfır bağımlılık
- NER/GLiNER: `transformers`, `torch`, `huggingface-hub`, `gliner`

---

## Lisans

MIT

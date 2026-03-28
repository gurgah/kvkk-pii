# kvkk-pii — Proje Özeti

KVKK uyumlu, Türkçe öncelikli, tamamen on-prem çalışan open source Python PII detection kütüphanesi.

## Temel Kararlar

- **Cloud yok** — kullanıcı modeli kendi makinesine indirir, veri dışarı çıkmaz
- **Presidio kullanılmaz** — sıfırdan, sade bir layered mimari
- **3 katmanlı sistem**: Regex → XLM-RoBERTa NER → GLiNER (isteğe bağlı)
- **Dil**: Python 3.10+, tip annotasyonları zorunlu

## Katman Mimarisi

| Katman | Yöntem | Model | Hız | Ne tespit eder |
|--------|--------|-------|-----|----------------|
| 1 | Regex + checksum | — | <1ms | TC Kimlik, IBAN, VKN, telefon, plaka, e-posta, pasaport |
| 2 | NER | `akdeniz27/xlm-roberta-base-turkish-ner` (~450MB) | ~30ms | PERSON, ORG, LOC |
| 3 | Zero-shot NER | `urchade/gliner_multi-v2.1` (~180MB) | ~80ms | KVKK Madde 6 özel kategoriler (sağlık, dini inanç, sendika) |

Layer 3 sadece isteğe bağlı aktif edilir — performans için varsayılan kapalı.

## KVKK Entity Listesi

**Tier 1 (Regex):**
- `TC_KIMLIK` — 11 haneli, checksum doğrulamalı
- `VKN` — 10 haneli vergi kimlik numarası
- `IBAN_TR` — TR prefix, 26 karakter
- `TELEFON_TR` — +90 5XX formatları
- `PLAKA_TR` — 01A 123 formatı
- `PASAPORT_TR`
- `EMAIL`
- `IP_ADRESI`

**Tier 2 (NER):**
- `KISI_ADI` (PERSON)
- `KONUM` (LOC)
- `KURUM` (ORG)

**Tier 3 (GLiNER, KVKK Madde 6):**
- `SAGLIK_VERISI`
- `DINI_INANC`
- `SIYASI_GORUS`
- `SENDIKA_UYELIGII`
- `BIYOMETRIK_VERI`

## Paket Yapısı

```
kvkk_pii/
├── __init__.py
├── detector.py          # Ana PiiDetector sınıfı
├── result.py            # PiiEntity, PiiResult dataclass'ları
├── layers/
│   ├── __init__.py
│   ├── regex_layer.py   # Layer 1
│   ├── ner_layer.py     # Layer 2
│   └── gliner_layer.py  # Layer 3
└── recognizers/
    ├── __init__.py
    ├── tc_kimlik.py
    ├── vkn.py
    ├── iban.py
    ├── telefon.py
    └── plaka.py
```

## Kurulum Hedefi

```bash
pip install kvkk-pii          # sadece regex (Layer 1)
pip install kvkk-pii[ner]     # + XLM-RoBERTa (Layer 2)
pip install kvkk-pii[full]    # + GLiNER (Layer 3)
```

## API Hedefi

```python
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])
result = detector.analyze("Ali Veli, TC: 12345678901, tel: 0532 123 45 67")
# result.entities → [PiiEntity(type="KISI_ADI", ...), PiiEntity(type="TC_KIMLIK", ...), ...]

anonymized = detector.anonymize(text)
# → "[KİŞİ_ADI], TC: [TC_KİMLİK], tel: [TELEFON_TR]"
```

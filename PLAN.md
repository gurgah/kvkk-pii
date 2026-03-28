# kvkk-pii — Geliştirme Planı

## Modüller

### 1. NER Layer (Layer 2) — `kvkk_pii/layers/ner_layer.py`
Zaten iskelet var, çalışır hale getirmek lazım.

**Ne yapılacak:**
- `akdeniz27/xlm-roberta-base-turkish-ner` ile HuggingFace pipeline entegrasyonu
- Regex'in bulduğu span'leri atla (overlap yönetimi mevcut)
- İlk çağrıda model indir, cache'le

**Test:** "Ahmet Yılmaz İstanbul'daki Türk Telekom şubesine gitti" → KISI_ADI + KONUM + KURUM

---

### 2. PiiSession — `kvkk_pii/session.py`
LLM proxy kullanımı için reversible maskeleme.

**Akış:**
```
prompt → session.mask() → AI'ya git → session.restore(response)
```

**Nasıl çalışır:**
- Her entity'ye benzersiz placeholder üret: `[TC_KIMLIK_a3f]`
- Mapping'i session içinde tut: `{"[TC_KIMLIK_a3f]": "10000000146"}`
- `restore()` ile response'daki placeholder'ları orijinale çevir

**API:**
```python
session = detector.create_session()
masked  = session.mask("Ali Veli TC: 10000000146")
# → "[KISI_ADI_x7k] TC: [TC_KIMLIK_a3f]"

ai_response = call_openai(masked)

restored = session.restore(ai_response)
# → "Ali Veli hakkında bilgi bulunamadı"
```

**Detaylar:**
- Aynı değer tekrar geçerse aynı placeholder kullan (tutarlılık)
- Thread-safe değil (her request yeni session almalı)
- Session'ı serialize edip saklama yok — ephemeral

---

### 3. LeakageAnalyzer — `kvkk_pii/leakage.py`
AI çıktısını tara — sızdı mı, ne sızdı?

**Üç kontrol:**

```
A) Output'ta maskelenmemiş PII var mı?
   AI cevabında yeni/beklenmedik PII tespit et

B) Session'daki masked entity'ler response'a sızdı mı?
   AI "[KISI_ADI_x7k]" yerine "Ali Veli" mi dedi?

C) AI kendi başına PII ürettí mi (hallucination)?
   Input'ta olmayan ama output'ta çıkan PII
```

**API:**
```python
analyzer = LeakageAnalyzer(detector)

report = analyzer.analyze(
    session=session,          # mask/restore mapping'i
    ai_response=raw_response, # restore EDİLMEMİŞ ham AI çıktısı
)

report.leaked_entities   # AI'dan sızan PII listesi
report.hallucinated      # Input'ta olmayıp output'ta çıkan PII
report.risk_score        # 0.0-1.0 genel risk
report.safe              # bool: herhangi bir sızıntı var mı
```

**Kullanım senaryosu:**
```python
masked = session.mask(user_prompt)
raw_response = call_openai(masked)

report = analyzer.analyze(session, raw_response)
if not report.safe:
    # Loglama, uyarı, ya da response'u engelle
    raise PiiLeakageError(report)

restored = session.restore(raw_response)
```

---

## Öncelik Sırası

| # | Modül | Bağımlılık | Durum |
|---|-------|-----------|-------|
| 1 | NER Layer | transformers, torch | Bekliyor |
| 2 | PiiSession | — (sadece detector) | Bekliyor |
| 3 | LeakageAnalyzer | PiiSession + detector | Bekliyor |
| 4 | GLiNER Layer | gliner | Bekliyor |

---

## Tam Proxy Akışı (hepsi birleşince)

```
user_prompt
    │
    ▼
session = detector.create_session()
masked = session.mask(user_prompt)        ← Regex + NER + GLiNER
    │
    ▼
raw_ai_response = call_ai_api(masked)
    │
    ├── report = analyzer.analyze(session, raw_ai_response)
    │       ├── if not report.safe → logla / engelle / uyar
    │       └── report.risk_score → audit log'a yaz
    │
    ▼
restored = session.restore(raw_ai_response)
    │
    ▼
kullanıcıya döner
```

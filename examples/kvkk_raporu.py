"""
Senaryo: Bir belgeyi KVKK açısından tara, uyum raporu üret.

Hukuk firmaları, muhasebe büroları veya sağlık kuruluşları
işledikleri belgelerde hangi KVKK maddelerini ihlal ettiklerini
bu araçla tespit edebilir.

Kurulum:
    pip install kvkk-pii[full]

Çalıştırma:
    python examples/kvkk_raporu.py
    python examples/kvkk_raporu.py --dosya belge.txt --json
"""
import argparse
import json
from kvkk_pii import PiiDetector

# Tüm katmanlar — KVKK Madde 6 dahil
detector = PiiDetector(layers=["regex", "ner", "gliner"])

ORNEK_BELGE = """
HASTA KABUL FORMU

Ad Soyad    : Fatma Kaya
TC Kimlik   : 10000000146
Telefon     : 0532 123 45 67
E-posta     : fatma.kaya@example.com
Adres       : Bağcılar Cad. No:12, İstanbul

Tanı        : Tip 2 diyabet, hipertansiyon
Sendika     : Türk Sağlık-Sen üyesi

Doktor      : Dr. Mehmet Demir
Kurum       : Özel Sağlık Hastanesi
"""


def rapor_olustur(metin: str, json_cikti: bool = False) -> None:
    sonuc = detector.analyze(metin)
    rapor = detector.compliance_report(metin)

    if json_cikti:
        cikti = {
            "entity_listesi": [
                {
                    "tur": e.entity_type,
                    "metin": e.text,
                    "konum": f"{e.start}-{e.end}",
                    "katman": e.layer,
                    "skor": round(e.score, 3),
                }
                for e in sonuc.entities
            ],
            "uyum_raporu": rapor.to_dict(),
        }
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("KVKK UYUM TARAMA RAPORU")
    print("=" * 60)

    print(f"\nTespit edilen veri sayısı : {len(sonuc.entities)}")
    print(f"Genel risk seviyesi       : {rapor.overall_risk.upper()}")
    print(f"Madde 6 ihlali            : {'EVET ⚠️' if rapor.has_madde6 else 'Hayır'}")

    print("\n--- Tespit Edilen Veriler ---")
    for e in sonuc.entities:
        print(f"  [{e.entity_type:20s}] {e.text!r:30s}  (katman: {e.layer})")

    print("\n--- KVKK Madde Analizi ---")
    print(rapor.summary())

    print("\n--- Anonimleştirilmiş Belge ---")
    print(sonuc.anonymize())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KVKK uyum raporu üret")
    parser.add_argument("--dosya", help="Taranacak metin dosyası")
    parser.add_argument("--json", action="store_true", help="JSON formatında çıktı ver")
    args = parser.parse_args()

    if args.dosya:
        with open(args.dosya, encoding="utf-8") as f:
            metin = f.read()
    else:
        print("(Örnek belge kullanılıyor — kendi dosyanız için: --dosya belge.txt)\n")
        metin = ORNEK_BELGE

    rapor_olustur(metin, json_cikti=args.json)

"""
Senaryo: Uygulama loglarını KVKK uyumlu hale getir.

Loglar genellikle kişisel veri sızdırır — IP adresi, e-posta,
hatta TC kimlik numarası. Bu script log satırlarını tarar ve
kişisel verileri maskeler.

Kurulum:
    pip install kvkk-pii

Çalıştırma:
    python examples/log_temizleyici.py
    python examples/log_temizleyici.py --dosya uygulama.log
"""
import argparse
import logging
import sys
from kvkk_pii import PiiDetector

detector = PiiDetector()


class KvkkLogFilter(logging.Filter):
    """Tüm log mesajlarından kişisel veriyi otomatik temizler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = detector.anonymize(str(record.msg))
        if record.args:
            record.args = tuple(
                detector.anonymize(str(a)) if isinstance(a, str) else a
                for a in (record.args if isinstance(record.args, tuple) else (record.args,))
            )
        return True


def dosya_temizle(girdi_yolu: str, cikti_yolu: str) -> None:
    """Bir log dosyasını satır satır temizler."""
    temizlenen = 0
    toplam = 0

    with open(girdi_yolu, encoding="utf-8") as f_in, \
         open(cikti_yolu, "w", encoding="utf-8") as f_out:

        for satir in f_in:
            toplam += 1
            temiz = detector.anonymize(satir.rstrip())
            f_out.write(temiz + "\n")
            if temiz != satir.rstrip():
                temizlenen += 1

    print(f"Tamamlandı: {toplam} satır işlendi, {temizlenen} satırda PII temizlendi.")
    print(f"Çıktı: {cikti_yolu}")


def demo() -> None:
    """Canlı demo — logging modülüne filtre ekle."""
    logger = logging.getLogger("uygulama")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.addFilter(KvkkLogFilter())

    print("=== KVKK Log Filtresi Aktif ===\n")

    # Bu loglar otomatik temizlenir
    logger.info("Kullanıcı 0532 123 45 67 ile giriş yaptı")
    logger.warning("Başarısız giriş denemesi: ali.veli@example.com, IP: 192.168.1.100")
    logger.error("Ödeme hatası — IBAN: TR33 0006 1005 1978 6457 8413 26")
    logger.info("Sipariş oluşturuldu: TC 10000000146, Ahmet Yılmaz")
    logger.debug("Temiz log satırı — kişisel veri yok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log dosyasını KVKK uyumlu hale getir")
    parser.add_argument("--dosya", help="Temizlenecek log dosyası")
    parser.add_argument("--cikti", help="Temizlenmiş dosyanın kaydedileceği yer")
    args = parser.parse_args()

    if args.dosya:
        cikti = args.cikti or args.dosya.replace(".log", "_temiz.log")
        dosya_temizle(args.dosya, cikti)
    else:
        demo()

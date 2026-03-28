"""
Senaryo: ChatGPT'ye müşteri verisi göndermeden önce maskele.

Kurulum:
    pip install kvkk-pii[ner] openai

Çalıştırma:
    OPENAI_API_KEY=sk-... python examples/chatgpt_proxy.py
"""
import os
from kvkk_pii import PiiDetector

detector = PiiDetector(layers=["regex", "ner"])

musteri_mesaji = """
Merhaba, TC kimlik numaram 10000000146.
0532 123 45 67 numaralı telefonumdan sipariş verdim ama
ali.veli@example.com adresime fatura gelmedi.
Ahmet Yılmaz adına kayıtlı sipariş nerede?
"""

print("=== Orijinal Mesaj ===")
print(musteri_mesaji)

# --- Gerçek OpenAI çağrısı (API key varsa) ---
def ai_cagri(maskeli_metin: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        import openai
        client = openai.OpenAI(api_key=api_key)
        yanit = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Müşteri hizmetleri asistanısın. Kısa yanıt ver."},
                {"role": "user", "content": maskeli_metin},
            ],
        )
        return yanit.choices[0].message.content
    else:
        # Demo modu — sahte yanıt
        return (
            "Merhaba, siparişinizi kontrol ettim. "
            "[KISI_ADI_x7k] adına kayıtlı [TC_KIMLIK_a3f] numaralı müşterimizin "
            "siparişi kargoya verilmiş durumda. "
            "[EMAIL_b2m] adresinize fatura 24 saat içinde iletilecek."
        )

# --- İki yönlü proxy akışı ---
sonuc = detector.two_way(
    prompt=musteri_mesaji,
    call_fn=ai_cagri,
    on_leak="warn",
)

print("\n=== Maskeli Mesaj (AI'ya giden) ===")
print(sonuc.masked_prompt)

print("\n=== AI Ham Yanıtı ===")
print(sonuc.raw_ai_output)

print("\n=== Geri Yüklenmiş Yanıt (kullanıcıya giden) ===")
print(sonuc.output)

print("\n=== Güvenlik Raporu ===")
print(f"Güvenli: {sonuc.report.safe}")
print(f"Risk skoru: {sonuc.report.risk_score:.2f}")
if not sonuc.report.safe:
    print(sonuc.report.summary())

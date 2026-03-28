"""
KVKK Uyum Raporu -- tespit edilen PII'i KVKK maddeleriyle iliskilendir.

Kullanim:
    report = ComplianceReport.from_result(result)
    print(report.summary())
    report.to_dict()  # JSON export icin
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from .result import PiiResult, PiiEntity

RiskLevel = Literal["düşük", "orta", "yüksek", "kritik"]

# Entity type -> KVKK maddesi + aciklama
_KVKK_MAP: dict[str, dict] = {
    "TC_KIMLIK": {
        "madde": "KVKK Madde 6 değil — Kimlik verisi (Madde 4/ç)",
        "kategori": "Kimlik Verisi",
        "risk": "yüksek",
        "oneri": "İşleme için açık rıza veya kanuni dayanak gerekli.",
    },
    "VKN": {
        "madde": "Kimlik Verisi (Madde 4/ç)",
        "kategori": "Kimlik Verisi",
        "risk": "orta",
        "oneri": "Vergi kaydı amaçlı işleme meşru menfaatle yapılabilir.",
    },
    "IBAN_TR": {
        "madde": "Finansal Veri (Madde 4/ç)",
        "kategori": "Finansal Veri",
        "risk": "yüksek",
        "oneri": "Ödeme işlemleri dışında saklanmamalı.",
    },
    "KREDI_KARTI": {
        "madde": "Finansal Veri (Madde 4/ç)",
        "kategori": "Finansal Veri",
        "risk": "kritik",
        "oneri": "PCI-DSS uyumu zorunlu. Kart numarası asla loglanmamalı.",
    },
    "TELEFON_TR": {
        "madde": "İletişim Verisi (Madde 4/ç)",
        "kategori": "İletişim Verisi",
        "risk": "orta",
        "oneri": "Pazarlama amacıyla işleme için açık rıza gerekli (İYS).",
    },
    "EMAIL": {
        "madde": "İletişim Verisi (Madde 4/ç)",
        "kategori": "İletişim Verisi",
        "risk": "orta",
        "oneri": "Ticari elektronik ileti için İYS kaydı gerekli.",
    },
    "KISI_ADI": {
        "madde": "Kişisel Veri (Madde 3/d)",
        "kategori": "Kimlik Verisi",
        "risk": "düşük",
        "oneri": "Diğer verilerle birleştiğinde risk artar.",
    },
    "KONUM": {
        "madde": "Konum Verisi (Madde 4/ç)",
        "kategori": "Konum Verisi",
        "risk": "orta",
        "oneri": "Sürekli konum takibi için açık rıza gerekli.",
    },
    "ADRES": {
        "madde": "Konum Verisi (Madde 4/ç)",
        "kategori": "Konum Verisi",
        "risk": "orta",
        "oneri": "Adres verisi kimlikle birleşince yüksek risk.",
    },
    "SAGLIK_VERISI": {
        "madde": "KVKK Madde 6 — Özel Nitelikli Kişisel Veri",
        "kategori": "Özel Nitelikli Veri",
        "risk": "kritik",
        "oneri": "Açık rıza zorunlu. Yetkili kurum olmadan işlenemez.",
    },
    "DINI_INANC": {
        "madde": "KVKK Madde 6 — Özel Nitelikli Kişisel Veri",
        "kategori": "Özel Nitelikli Veri",
        "risk": "kritik",
        "oneri": "Açık rıza zorunlu. Kural olarak işlenemez.",
    },
    "SIYASI_GORUS": {
        "madde": "KVKK Madde 6 — Özel Nitelikli Kişisel Veri",
        "kategori": "Özel Nitelikli Veri",
        "risk": "kritik",
        "oneri": "Açık rıza zorunlu. Kural olarak işlenemez.",
    },
    "SENDIKA_UYELIGII": {
        "madde": "KVKK Madde 6 — Özel Nitelikli Kişisel Veri",
        "kategori": "Özel Nitelikli Veri",
        "risk": "kritik",
        "oneri": "Açık rıza zorunlu. Kural olarak işlenemez.",
    },
    "BIYOMETRIK_VERI": {
        "madde": "KVKK Madde 6 — Özel Nitelikli Kişisel Veri",
        "kategori": "Özel Nitelikli Veri",
        "risk": "kritik",
        "oneri": "Açık rıza zorunlu. Güvenli ortamda saklanmalı.",
    },
    "SGK_NO": {
        "madde": "Kimlik Verisi (Madde 4/ç)",
        "kategori": "Kimlik Verisi",
        "risk": "yüksek",
        "oneri": "SGK işlemleri dışında işlenemez.",
    },
    "IP_ADRESI": {
        "madde": "Kişisel Veri (Madde 3/d) — bağlamsal",
        "kategori": "Teknik Veri",
        "risk": "düşük",
        "oneri": "Dinamik IP tek başına kişisel veri sayılmayabilir.",
    },
    "PLAKA_TR": {
        "madde": "Kimlik Verisi (Madde 4/ç) — dolaylı",
        "kategori": "Kimlik Verisi",
        "risk": "düşük",
        "oneri": "Araç sahibiyle ilişkilendirildiğinde kişisel veri.",
    },
}

_RISK_ORDER = {"düşük": 0, "orta": 1, "yüksek": 2, "kritik": 3}


@dataclass
class Violation:
    entity_type: str
    count: int
    madde: str
    kategori: str
    risk: RiskLevel
    oneri: str
    samples: list[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    violations: list[Violation]
    overall_risk: RiskLevel
    entity_count: int
    has_madde6: bool

    @classmethod
    def from_result(cls, result: PiiResult, max_samples: int = 3) -> "ComplianceReport":
        # Entity type basina grupla
        by_type: dict[str, list[PiiEntity]] = {}
        for e in result.entities:
            by_type.setdefault(e.entity_type, []).append(e)

        violations: list[Violation] = []
        for entity_type, entities in by_type.items():
            mapping = _KVKK_MAP.get(entity_type)
            if not mapping:
                continue
            violations.append(Violation(
                entity_type=entity_type,
                count=len(entities),
                madde=mapping["madde"],
                kategori=mapping["kategori"],
                risk=mapping["risk"],
                oneri=mapping["oneri"],
                samples=[e.text for e in entities[:max_samples]],
            ))

        # En yuksek risk seviyesi
        if violations:
            overall_risk = max(violations, key=lambda v: _RISK_ORDER[v.risk]).risk
        else:
            overall_risk = "düşük"

        has_madde6 = any(v.kategori == "Özel Nitelikli Veri" for v in violations)

        # Risk seviyesine gore sirala
        violations.sort(key=lambda v: _RISK_ORDER[v.risk], reverse=True)

        return cls(
            violations=violations,
            overall_risk=overall_risk,
            entity_count=len(result.entities),
            has_madde6=has_madde6,
        )

    def summary(self) -> str:
        if not self.violations:
            return "KVKK ihlali tespit edilmedi."

        lines = [
            f"KVKK Uyum Raporu — {self.entity_count} veri, genel risk: {self.overall_risk.upper()}",
        ]
        if self.has_madde6:
            lines.append("KVKK Madde 6 (Özel Nitelikli Veri) tespit edildi!")
        lines.append("")
        for v in self.violations:
            lines.append(f"  [{v.risk.upper()}] {v.entity_type} x {v.count}")
            lines.append(f"    Dayanak: {v.madde}")
            lines.append(f"    Öneri  : {v.oneri}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "overall_risk": self.overall_risk,
            "entity_count": self.entity_count,
            "has_madde6": self.has_madde6,
            "violations": [
                {
                    "entity_type": v.entity_type,
                    "count": v.count,
                    "madde": v.madde,
                    "kategori": v.kategori,
                    "risk": v.risk,
                    "oneri": v.oneri,
                    "samples": v.samples,
                }
                for v in self.violations
            ],
        }

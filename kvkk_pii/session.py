"""
PiiSession — LLM proxy kullanımı için reversible maskeleme.

Her request için yeni bir session oluştur.
Session ephemeral'dır — serialize edilmez, saklanmaz.
"""
from __future__ import annotations
import random
import re
import string
from dataclasses import dataclass, field

from .result import PiiEntity, PiiResult


def _short_id() -> str:
    """3 karakterli rastgele alfanumerik ID üret."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=3))


@dataclass
class MaskedEntity:
    entity: PiiEntity
    placeholder: str   # örn. "[TC_KIMLIK_a3f]"
    original: str      # orijinal metin


class PiiSession:
    """
    Kullanım:
        session = detector.create_session()
        masked  = session.mask("Ali Veli TC: 10000000146")
        # → "[KISI_ADI_x7k] TC: [TC_KIMLIK_a3f]"

        restored = session.restore("[KISI_ADI_x7k] bulunamadı")
        # → "Ali Veli bulunamadı"
    """

    def __init__(self, result: PiiResult) -> None:
        self._result = result
        # orijinal değer → placeholder (aynı değer tekrar geçerse aynı placeholder)
        self._value_to_placeholder: dict[str, str] = {}
        # placeholder → orijinal değer (restore için)
        self._placeholder_to_value: dict[str, str] = {}
        self.masked_entities: list[MaskedEntity] = []

    def _get_or_create_placeholder(self, entity: PiiEntity) -> str:
        key = entity.text
        if key in self._value_to_placeholder:
            return self._value_to_placeholder[key]

        uid = _short_id()
        # Çakışma ihtimaline karşı yeniden üret
        while f"[{entity.entity_type}_{uid}]" in self._placeholder_to_value:
            uid = _short_id()

        placeholder = f"[{entity.entity_type}_{uid}]"
        self._value_to_placeholder[key] = placeholder
        self._placeholder_to_value[placeholder] = key
        return placeholder

    def mask(self, text: str | None = None) -> str:
        """
        Session'ın analiz ettiği metni maskele.
        text=None ise orijinal analiz metnini kullanır.
        """
        source = text if text is not None else self._result.text
        if text is not None and text != self._result.text:
            # Farklı metin verilmişse yeniden analiz et — session'ı güncelle
            raise ValueError(
                "mask() orijinal metinle çağrılmalı. "
                "Farklı metin için yeni session oluştur."
            )

        result = source
        # Sondan başa doğru değiştir — index kayması olmasın
        for entity in sorted(self._result.entities, key=lambda e: e.start, reverse=True):
            placeholder = self._get_or_create_placeholder(entity)
            self.masked_entities.append(
                MaskedEntity(entity=entity, placeholder=placeholder, original=entity.text)
            )
            result = result[: entity.start] + placeholder + result[entity.end :]

        return result

    def restore(self, masked_text: str) -> str:
        """AI response'undaki placeholder'ları orijinal değerlerle değiştir."""
        result = masked_text
        # Uzun placeholder'ları önce işle — kısa olanların içinde geçmesi olasılığına karşı
        for placeholder, original in sorted(
            self._placeholder_to_value.items(), key=lambda x: -len(x[0])
        ):
            result = result.replace(placeholder, original)
        return result

    @property
    def mapping(self) -> dict[str, str]:
        """placeholder → orijinal değer haritası (audit/debug için)."""
        return dict(self._placeholder_to_value)

    def __repr__(self) -> str:
        return f"PiiSession(entities={len(self.masked_entities)}, placeholders={len(self._placeholder_to_value)})"

"""
翻译服务
"""
import hashlib
from typing import List

from app.services.storage.repositories import StorageRepository


class TranslatorService:
    """翻译业务服务"""

    def __init__(self, repository: StorageRepository) -> None:
        self._repository = repository

    def _hash(self, text: str, source_lang: str, target_lang: str) -> str:
        value = f"{source_lang}:{target_lang}:{text}"
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    async def translate(self, text: str, source_lang: str, target_lang: str) -> dict:
        source_hash = self._hash(text, source_lang, target_lang)
        cached = await self._repository.get_translation_cache(source_hash)
        if cached:
            return {"translatedText": cached.translatedText, "cached": True}

        translated = text if source_lang == target_lang else text
        await self._repository.save_translation_cache(
            source_hash=source_hash,
            source_lang=source_lang,
            target_lang=target_lang,
            translated_text=translated,
        )
        return {"translatedText": translated, "cached": False}

    async def translate_batch(self, items: List[dict]) -> List[dict]:
        results = []
        for item in items:
            result = await self.translate(
                text=item["text"],
                source_lang=item.get("sourceLang", "auto"),
                target_lang=item["targetLang"],
            )
            results.append(result)
        return results

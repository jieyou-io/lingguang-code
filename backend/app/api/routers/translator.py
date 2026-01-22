"""
翻译路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.translator import (
    TranslateRequest,
    TranslateResponse,
    TranslateBatchRequest,
    TranslateBatchResponse,
    TranslateBatchResponseItem,
)
from app.services.storage.repositories import StorageRepository
from app.services.translator.service import TranslatorService

router = APIRouter()


def build_service(session) -> TranslatorService:
    repository = StorageRepository(session)
    return TranslatorService(repository)


@router.post(
    "/v1/translate",
    response_model=TranslateResponse,
    summary="翻译文本",
    description="翻译单段文本，返回译文与缓存命中信息。",
)
async def translate(
    payload: TranslateRequest,
    session=Depends(get_db_session),
):
    service = build_service(session)
    result = await service.translate(
        text=payload.text,
        source_lang=payload.sourceLang,
        target_lang=payload.targetLang,
    )
    return TranslateResponse(**result)


@router.post(
    "/v1/translate/batch",
    response_model=TranslateBatchResponse,
    summary="批量翻译",
    description="批量翻译多个文本条目，返回逐条结果。",
)
async def translate_batch(
    payload: TranslateBatchRequest,
    session=Depends(get_db_session),
):
    service = build_service(session)
    results = await service.translate_batch([item.model_dump() for item in payload.items])
    return TranslateBatchResponse(
        items=[TranslateBatchResponseItem(**item) for item in results]
    )

"""
翻译请求/响应模型
"""
from typing import List
from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., description="待翻译文本")
    sourceLang: str = Field(default="auto", description="源语言")
    targetLang: str = Field(..., description="目标语言")


class TranslateResponse(BaseModel):
    translatedText: str
    cached: bool


class TranslateBatchItem(BaseModel):
    text: str
    sourceLang: str = Field(default="auto")
    targetLang: str


class TranslateBatchRequest(BaseModel):
    items: List[TranslateBatchItem]


class TranslateBatchResponseItem(BaseModel):
    translatedText: str
    cached: bool


class TranslateBatchResponse(BaseModel):
    items: List[TranslateBatchResponseItem]

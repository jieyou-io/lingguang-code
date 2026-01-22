"""
统一错误格式模块

定义标准的 API 错误响应格式
"""
import logging
from typing import Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: ErrorDetail


class APIError(HTTPException):
    """自定义 API 错误"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """API 错误处理器"""
    logger.error(
        "api_error",
        code=exc.code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.exception(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if logger.isEnabledFor(logging.DEBUG) else None,
            }
        },
    )


# 常用错误
class SessionNotFoundError(APIError):
    """会话未找到"""
    def __init__(self, session_id: str):
        super().__init__(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Session not found: {session_id}",
        )


class InvalidParameterError(APIError):
    """无效参数"""
    def __init__(self, param: str, reason: str):
        super().__init__(
            status_code=400,
            code="INVALID_PARAMETER",
            message=f"Invalid parameter: {param}",
            details=reason,
        )


class ServiceUnavailableError(APIError):
    """服务不可用"""
    def __init__(self, service: str):
        super().__init__(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message=f"Service unavailable: {service}",
        )

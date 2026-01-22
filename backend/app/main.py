"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import api_error_handler, general_exception_handler, APIError
from app.core.logging import setup_logging
from app.api.routers import (
    health,
    claude,
    codex,
    gemini,
    mcp,
    translator,
    context_manager,
    usage,
    projects,
    prompts,
    system_prompts,
    claude_agents,
    claude_skills,
    claude_plugins,
    providers,
    sessions,
    engine_status,
    models,
)

# 初始化日志
setup_logging()

# 创建 FastAPI 应用
app = FastAPI(
    title="Any Code Backend API",
    description="三引擎 AI 代码助手后端服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["Health"])
app.include_router(engine_status.router, tags=["Engine Status"])
app.include_router(claude.router, tags=["Claude"])
app.include_router(codex.router, tags=["Codex"])
app.include_router(gemini.router, tags=["Gemini"])
app.include_router(mcp.router, tags=["MCP"])
app.include_router(translator.router, tags=["Translator"])
app.include_router(context_manager.router, tags=["ContextManager"])
app.include_router(usage.router, tags=["Usage"])

# 新增配置管理路由
app.include_router(projects.router, tags=["Projects"])
app.include_router(sessions.router, tags=["Sessions"])
app.include_router(prompts.router, tags=["Prompts"])
app.include_router(system_prompts.router, tags=["System Prompts"])
app.include_router(claude_agents.router, tags=["Claude Agents"])
app.include_router(claude_skills.router, tags=["Claude Skills"])
app.include_router(claude_plugins.router, tags=["Claude Plugins"])
app.include_router(providers.router, tags=["Providers"])
app.include_router(models.router, tags=["Models"])

# 异常处理
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    import structlog

    logger = structlog.get_logger()
    logger.info("application_startup", version="1.0.0")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    import structlog
    logger = structlog.get_logger()
    logger.info("application_shutdown")

# 根路径
@app.get(
    "/",
    summary="服务信息",
    description="返回服务名称、版本与运行状态。",
)
async def root():
    """根路径"""
    return {
        "service": "Any Code Backend API",
        "version": "1.0.0",
        "status": "running"
    }

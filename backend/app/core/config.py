"""
配置管理模块

使用 pydantic-settings 从环境变量加载配置
优先级: 环境变量 > .env 文件 > 默认值
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    APP_NAME: str = "Any Code Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "production"
    DEBUG: bool = False

    # 服务器配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    # CLI 配置路径
    CLAUDE_CLI_PATH: str = "claude"
    CODEX_CLI_PATH: str = "codex"
    GEMINI_CLI_PATH: str = "gemini"

    # 进程管理配置
    MAX_CONCURRENT_SESSIONS: int = 10
    SESSION_TIMEOUT_SECONDS: int = 1800  # 30 分钟

    # SSE 配置
    SSE_KEEPALIVE_SECONDS: int = 15

    # Claude 权限自动授权（Web/飞书默认 y）
    CLAUDE_AUTO_APPROVE_PERMISSIONS: bool = True

    # 日志配置
    LOG_LEVEL: str = "info"
    LOG_JSON: bool = True

    # Feishu Bot 配置
    FEISHU_ENABLE: bool = False
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_BOT_NAME: str = "FeishuBot"
    FEISHU_ENCRYPT_KEY: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_BOT_OPEN_ID: str = ""
    FEISHU_STATE_PATH: str = "~/.anycode/feishu_state.json"
    FEISHU_DEFAULT_ENGINE: str = "claude"
    FEISHU_DEFAULT_MODEL: str = "claude-sonnet-4-5"
    FEISHU_REQUIRE_MENTION_DEFAULT: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

# 全局配置实例
settings = Settings()

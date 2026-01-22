# 灵光后端 (FastAPI)

<a href="README_en.md">English</a> | <b>中文</b>

灵光后端服务，主要用于对接本地 AI CLI（Claude、Codex、Gemini），提供统一的会话与流式接口。

## 运行环境
- Python 3.11+

## 快速开始（本地）
1) 创建环境变量文件：
   - 复制 `.env.example` 为 `.env` 并修改配置。

2) 安装依赖：
   - `pip install -r requirements.txt`

3) 启动 API：
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## 健康检查
- `GET /health`

## 备注
- API 使用 camelCase 字段。
- SSE 保活由 `SSE_KEEPALIVE_SECONDS` 控制（默认 15 秒）。
- 会话超时为 `SESSION_TIMEOUT_SECONDS`（默认 1800 秒）。
- 最大并发会话数：`MAX_CONCURRENT_SESSIONS`（默认 10）。

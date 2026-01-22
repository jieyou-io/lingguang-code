"""
使用统计服务

"""
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import structlog

logger = structlog.get_logger()


class UsageService:
    """使用统计业务服务"""

    def __init__(self) -> None:
        self._claude_dir = Path.home() / ".claude"
        self._codex_dir = Path.home() / ".codex"
        self._gemini_dir = Path.home() / ".gemini"

    async def get_stats(self, days: Optional[int] = None) -> dict:
        """
        获取使用统计

        Args:
            days: 统计最近 N 天的数据,None 表示全部

        Returns:
            统计数据字典
        """
        all_entries = self._get_all_usage_entries()

        if not all_entries:
            return self._empty_stats()

        # 按天数过滤
        if days is not None:
            cutoff = datetime.now().date() - timedelta(days=days)
            all_entries = [
                e for e in all_entries
                if self._parse_timestamp(e.get("timestamp", "")).date() >= cutoff
            ]

        return self._calculate_stats(all_entries)

    def _get_all_usage_entries(self) -> List[Dict]:
        """从三个引擎目录读取所有使用记录"""
        all_entries = []
        processed_hashes = set()

        # 1. 读取 Claude 会话数据
        all_entries.extend(self._get_claude_entries(processed_hashes))

        # 2. 读取 Codex 会话数据
        all_entries.extend(self._get_codex_entries(processed_hashes))

        # 3. 读取 Gemini 会话数据
        all_entries.extend(self._get_gemini_entries(processed_hashes))

        # 按时间戳排序
        all_entries.sort(key=lambda e: e.get("timestamp", ""))
        return all_entries

    def _get_claude_entries(self, processed_hashes: set) -> List[Dict]:
        """读取 Claude 会话数据"""
        projects_dir = self._claude_dir / "projects"
        if not projects_dir.exists():
            return []

        all_entries = []
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name
            for jsonl_file in project_dir.glob("*.jsonl"):
                entries = self._parse_session_jsonl_file(jsonl_file, project_name, processed_hashes)
                all_entries.extend(entries)

        return all_entries

    def _get_codex_entries(self, processed_hashes: set) -> List[Dict]:
        """读取 Codex 会话数据"""
        sessions_dir = self._codex_dir / "sessions"
        if not sessions_dir.exists():
            return []

        all_entries = []
        # Codex 会话按日期组织: ~/.codex/sessions/YYYY/MM/DD/*.jsonl
        for jsonl_file in sessions_dir.rglob("*.jsonl"):
            entries = self._parse_codex_session_file(jsonl_file, processed_hashes)
            all_entries.extend(entries)

        return all_entries

    def _get_gemini_entries(self, processed_hashes: set) -> List[Dict]:
        """读取 Gemini 会话数据"""
        # Gemini 会话存储在: ~/.gemini/tmp/<project_hash>/chats/*.json
        tmp_dir = self._gemini_dir / "tmp"
        if not tmp_dir.exists():
            return []

        all_entries = []
        for json_file in tmp_dir.rglob("chats/*.json"):
            entries = self._parse_gemini_session_file(json_file, processed_hashes)
            all_entries.extend(entries)

        return all_entries

    def _parse_session_jsonl_file(self, file_path: Path, project_name: str, processed_hashes: set) -> List[Dict]:
        """
        解析会话 JSONL 文件，提取 usage 数据

        """
        entries = []
        session_id = file_path.stem  # 文件名即为 session_id
        actual_project_path = None

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # 提取项目路径（从 cwd 字段）
                        if actual_project_path is None:
                            cwd = data.get("cwd")
                            if cwd:
                                actual_project_path = cwd

                        # 提取 message.usage 数据
                        message = data.get("message")
                        if not message:
                            continue

                        usage = message.get("usage")
                        if not usage:
                            continue

                        # 提取 token 数据
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
                        cache_read_tokens = usage.get("cache_read_input_tokens", 0)

                        # 跳过无意义的记录
                        if input_tokens == 0 and output_tokens == 0 and cache_creation_tokens == 0 and cache_read_tokens == 0:
                            continue

                        # 去重（基于 message.id + request_id）
                        msg_id = message.get("id", "")
                        req_id = data.get("requestId", "")
                        if msg_id and req_id:
                            unique_hash = f"{msg_id}:{req_id}"
                            if unique_hash in processed_hashes:
                                continue
                            processed_hashes.add(unique_hash)

                        # 提取模型
                        model = message.get("model", "unknown")

                        # 计算成本
                        cost = data.get("costUSD")
                        if cost is None:
                            cost = self._calculate_cost(model, usage)

                        # 提取时间戳
                        timestamp = data.get("timestamp", "")

                        # 构建 usage entry
                        entry = {
                            "session_id": session_id,
                            "timestamp": timestamp,
                            "model": model,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cache_creation_tokens": cache_creation_tokens,
                            "cache_read_tokens": cache_read_tokens,
                            "cost": cost,
                            "project_path": actual_project_path or "",
                            "project_name": project_name,
                        }

                        entries.append(entry)

                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        return entries

    def _parse_codex_session_file(self, file_path: Path, processed_hashes: set) -> List[Dict]:
        """解析 Codex 会话文件"""
        entries = []
        session_id = file_path.stem
        actual_project_path = None

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # 提取项目路径（从 session_meta）
                        if data.get("type") == "session_meta" and actual_project_path is None:
                            payload = data.get("payload", {})
                            actual_project_path = payload.get("cwd", "")

                        # 提取 token_count 数据
                        if data.get("type") == "event_msg":
                            payload = data.get("payload", {})
                            if payload.get("type") == "token_count":
                                info = payload.get("info")
                                if not info:
                                    continue
                                last_usage = info.get("last_token_usage", {})

                                input_tokens = last_usage.get("input_tokens", 0)
                                output_tokens = last_usage.get("output_tokens", 0)
                                cached_tokens = last_usage.get("cached_input_tokens", 0)

                                if input_tokens == 0 and output_tokens == 0:
                                    continue

                                # 去重
                                timestamp = data.get("timestamp", "")
                                unique_hash = f"{session_id}:{timestamp}"
                                if unique_hash in processed_hashes:
                                    continue
                                processed_hashes.add(unique_hash)

                                # 构建 entry（Codex 使用 GPT 模型）
                                entry = {
                                    "session_id": session_id,
                                    "timestamp": timestamp,
                                    "model": "gpt-4",  # Codex 默认使用 GPT-4
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                    "cache_creation_tokens": 0,
                                    "cache_read_tokens": cached_tokens,
                                    "cost": 0.0,  # 稍后计算
                                    "project_path": actual_project_path or "",
                                }
                                entries.append(entry)

                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        return entries

    def _parse_gemini_session_file(self, file_path: Path, processed_hashes: set) -> List[Dict]:
        """解析 Gemini 会话文件"""
        entries = []
        session_id = file_path.stem

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

                # 提取项目路径
                actual_project_path = data.get("cwd", "")

                # 提取消息列表
                messages = data.get("messages", [])
                for msg in messages:
                    # 只处理 assistant 消息
                    if msg.get("role") != "model":
                        continue

                    # 提取 usage 数据
                    usage_metadata = msg.get("usageMetadata", {})
                    if not usage_metadata:
                        continue

                    input_tokens = usage_metadata.get("promptTokenCount", 0)
                    output_tokens = usage_metadata.get("candidatesTokenCount", 0)
                    cached_tokens = usage_metadata.get("cachedContentTokenCount", 0)

                    if input_tokens == 0 and output_tokens == 0:
                        continue

                    # 去重
                    timestamp = msg.get("timestamp", "")
                    unique_hash = f"{session_id}:{timestamp}"
                    if unique_hash in processed_hashes:
                        continue
                    processed_hashes.add(unique_hash)

                    # 构建 entry（Gemini 使用 GLM 模型）
                    entry = {
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "model": "glm-4",  # Gemini 默认使用 GLM-4
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_creation_tokens": 0,
                        "cache_read_tokens": cached_tokens,
                        "cost": 0.0,  # 稍后计算
                        "project_path": actual_project_path,
                    }
                    entries.append(entry)

        except (OSError, json.JSONDecodeError):
            pass

        return entries

    def _calculate_cost(self, model: str, usage: dict) -> float:
        """
        计算成本

        价格单位：每百万 tokens
        """
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
        cache_read_tokens = usage.get("cache_read_input_tokens", 0)

        model_lower = model.lower()

        # Claude 4.5 Opus
        if "opus" in model_lower and ("4.5" in model_lower or "4-5" in model_lower):
            return (
                input_tokens * 5.0 / 1_000_000
                + output_tokens * 25.0 / 1_000_000
                + cache_creation_tokens * 6.25 / 1_000_000
                + cache_read_tokens * 0.50 / 1_000_000
            )

        # Claude 4.5 Sonnet (默认)
        if "sonnet" in model_lower and ("4.5" in model_lower or "4-5" in model_lower):
            return (
                input_tokens * 3.0 / 1_000_000
                + output_tokens * 15.0 / 1_000_000
                + cache_creation_tokens * 3.75 / 1_000_000
                + cache_read_tokens * 0.30 / 1_000_000
            )

        # Claude 4.5 Haiku
        if "haiku" in model_lower and ("4.5" in model_lower or "4-5" in model_lower):
            return (
                input_tokens * 1.0 / 1_000_000
                + output_tokens * 5.0 / 1_000_000
                + cache_creation_tokens * 1.25 / 1_000_000
                + cache_read_tokens * 0.10 / 1_000_000
            )

        # Claude 4.1 Opus
        if "opus" in model_lower and ("4.1" in model_lower or "4-1" in model_lower):
            return (
                input_tokens * 15.0 / 1_000_000
                + output_tokens * 75.0 / 1_000_000
                + cache_creation_tokens * 18.75 / 1_000_000
                + cache_read_tokens * 1.50 / 1_000_000
            )

        # Generic fallback (使用 Sonnet 4.5 价格)
        if "sonnet" in model_lower or "claude" in model_lower:
            return (
                input_tokens * 3.0 / 1_000_000
                + output_tokens * 15.0 / 1_000_000
                + cache_creation_tokens * 3.75 / 1_000_000
                + cache_read_tokens * 0.30 / 1_000_000
            )

        # Unknown model
        return 0.0

    def _parse_jsonl_file(self, file_path: Path, project_name: str, processed_hashes: set) -> List[Dict]:
        """解析 JSONL 文件（旧逻辑，保留向后兼容）"""
        entries = []

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # 去重
                        content_hash = hash(json.dumps(data, sort_keys=True))
                        if content_hash in processed_hashes:
                            continue
                        processed_hashes.add(content_hash)

                        # 添加项目信息
                        data["project_name"] = project_name
                        entries.append(data)

                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        return entries

    def _calculate_stats(self, entries: List[Dict]) -> dict:
        """计算统计数据"""
        total_cost = 0.0
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation_tokens = 0
        total_cache_read_tokens = 0
        unique_sessions = set()

        model_stats = {}
        daily_stats = {}
        project_stats = {}
        engine_stats = {"claude": 0, "codex": 0, "gemini": 0}

        for entry in entries:
            # 累计总数
            cost = entry.get("cost", 0.0)
            input_tok = entry.get("input_tokens", 0)
            output_tok = entry.get("output_tokens", 0)
            cache_create = entry.get("cache_creation_tokens", 0)
            cache_read = entry.get("cache_read_tokens", 0)

            total_cost += cost
            total_input_tokens += input_tok
            total_output_tokens += output_tok
            total_cache_creation_tokens += cache_create
            total_cache_read_tokens += cache_read
            total_tokens += input_tok + output_tok + cache_create + cache_read

            session_id = entry.get("session_id", "")
            if session_id:
                unique_sessions.add(session_id)

            # 按模型统计
            model = entry.get("model", "unknown")
            if model not in model_stats:
                model_stats[model] = {
                    "model": model,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "session_count": 0,
                    "sessions": set(),
                }

            ms = model_stats[model]
            ms["total_cost"] += cost
            ms["input_tokens"] += input_tok
            ms["output_tokens"] += output_tok
            ms["cache_creation_tokens"] += cache_create
            ms["cache_read_tokens"] += cache_read
            ms["total_tokens"] += input_tok + output_tok + cache_create + cache_read
            if session_id:
                ms["sessions"].add(session_id)

            # 按引擎统计 (根据模型名称推断引擎)
            model_lower = model.lower()
            entry_tokens = input_tok + output_tok + cache_create + cache_read
            if "claude" in model_lower or "sonnet" in model_lower or "opus" in model_lower or "haiku" in model_lower:
                engine_stats["claude"] += entry_tokens
            elif "gpt" in model_lower or "codex" in model_lower:
                engine_stats["codex"] += entry_tokens
            elif "gemini" in model_lower or "glm" in model_lower:
                # Gemini 使用 GLM 模型（如 glm-4.7, glm-4.5-air）
                engine_stats["gemini"] += entry_tokens

            # 按日期统计
            timestamp = entry.get("timestamp", "")
            date = self._parse_timestamp(timestamp).strftime("%Y-%m-%d")
            if date not in daily_stats:
                daily_stats[date] = {
                    "date": date,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "models_used": set(),
                }

            ds = daily_stats[date]
            ds["total_cost"] += cost
            ds["total_tokens"] += input_tok + output_tok + cache_create + cache_read
            ds["models_used"].add(model)

            # 按项目统计
            project_name = entry.get("project_name", "unknown")
            if project_name not in project_stats:
                project_stats[project_name] = {
                    "project_name": project_name,
                    "project_path": entry.get("project_path", ""),
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "session_count": 0,
                    "sessions": set(),
                    "last_used": timestamp,
                }

            ps = project_stats[project_name]
            ps["total_cost"] += cost
            ps["total_tokens"] += input_tok + output_tok + cache_create + cache_read
            if session_id:
                ps["sessions"].add(session_id)
            if timestamp > ps["last_used"]:
                ps["last_used"] = timestamp

        # 转换为列表格式
        by_model = []
        for ms in model_stats.values():
            by_model.append({
                "model": ms["model"],
                "total_cost": ms["total_cost"],
                "total_tokens": ms["total_tokens"],
                "input_tokens": ms["input_tokens"],
                "output_tokens": ms["output_tokens"],
                "cache_creation_tokens": ms["cache_creation_tokens"],
                "cache_read_tokens": ms["cache_read_tokens"],
                "session_count": len(ms["sessions"]),
            })

        by_date = []
        for ds in daily_stats.values():
            by_date.append({
                "date": ds["date"],
                "total_cost": ds["total_cost"],
                "total_tokens": ds["total_tokens"],
                "models_used": list(ds["models_used"]),
            })
        by_date.sort(key=lambda x: x["date"], reverse=True)

        by_project = []
        for ps in project_stats.values():
            by_project.append({
                "project_path": ps["project_path"],
                "project_name": ps["project_name"],
                "total_cost": ps["total_cost"],
                "total_tokens": ps["total_tokens"],
                "session_count": len(ps["sessions"]),
                "last_used": ps["last_used"],
            })
        by_project.sort(key=lambda x: x["last_used"], reverse=True)

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cache_creation_tokens": total_cache_creation_tokens,
            "total_cache_read_tokens": total_cache_read_tokens,
            "total_sessions": len(unique_sessions),
            "by_model": by_model,
            "by_date": by_date,
            "by_project": by_project,
            "by_engine": engine_stats,
        }

    def _empty_stats(self) -> dict:
        """返回空统计数据"""
        return {
            "total_cost": 0.0,
            "total_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_creation_tokens": 0,
            "total_cache_read_tokens": 0,
            "total_sessions": 0,
            "by_model": [],
            "by_date": [],
            "by_project": [],
            "by_engine": {"claude": 0, "codex": 0, "gemini": 0},
        }

    def _parse_timestamp(self, timestamp: str) -> datetime:
        """解析时间戳，统一返回不带时区的 datetime"""
        try:
            # 解析 ISO 格式时间戳
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # 转换为不带时区的本地时间
            return dt.replace(tzinfo=None)
        except (ValueError, AttributeError):
            return datetime.now()

    async def get_session_stats(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        order: Optional[str] = None
    ) -> List[Dict]:
        """
        获取会话统计

        Args:
            since: 开始日期 (YYYYMMDD)
            until: 结束日期 (YYYYMMDD)
            order: 排序方式 (asc/desc)

        Returns:
            按项目统计的会话列表
        """
        all_entries = self._get_all_usage_entries()

        # 按日期范围过滤
        if since and until:
            try:
                since_date = datetime.strptime(since, "%Y%m%d").date()
                until_date = datetime.strptime(until, "%Y%m%d").date()

                all_entries = [
                    e for e in all_entries
                    if since_date <= self._parse_timestamp(e.get("timestamp", "")).date() <= until_date
                ]
            except ValueError:
                pass

        # 按项目聚合
        project_stats = {}
        for entry in all_entries:
            project_name = entry.get("project_name", "unknown")
            if project_name not in project_stats:
                project_stats[project_name] = {
                    "project_name": project_name,
                    "project_path": entry.get("project_path", ""),
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "sessions": set(),
                    "last_used": entry.get("timestamp", ""),
                }

            ps = project_stats[project_name]
            ps["total_cost"] += entry.get("cost", 0.0)
            ps["total_tokens"] += (
                entry.get("input_tokens", 0) +
                entry.get("output_tokens", 0) +
                entry.get("cache_creation_tokens", 0) +
                entry.get("cache_read_tokens", 0)
            )

            session_id = entry.get("session_id", "")
            if session_id:
                ps["sessions"].add(session_id)

            timestamp = entry.get("timestamp", "")
            if timestamp > ps["last_used"]:
                ps["last_used"] = timestamp

        # 转换为列表
        result = []
        for ps in project_stats.values():
            result.append({
                "project_path": ps["project_path"],
                "project_name": ps["project_name"],
                "total_cost": ps["total_cost"],
                "total_tokens": ps["total_tokens"],
                "session_count": len(ps["sessions"]),
                "last_used": ps["last_used"],
            })

        # 排序
        if order == "asc":
            result.sort(key=lambda x: x["last_used"])
        else:
            result.sort(key=lambda x: x["last_used"], reverse=True)

        return result

    async def get_quick_stats(
        self,
        project_path: Optional[str] = None
    ) -> dict:
        """
        获取快速统计 - 专为会话页面和项目页面设计

        Args:
            project_path: 项目路径,不传则统计所有项目

        Returns:
            快速统计数据 (今日/本周/本月)
        """
        all_entries = self._get_all_usage_entries()

        # 按项目过滤
        if project_path:
            all_entries = [
                e for e in all_entries
                if e.get("project_path", "") == project_path
            ]

        # 计算今日、本周、本月的统计
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        today_stats = {"tokens": 0, "cost": 0.0, "sessions": set()}
        week_stats = {"tokens": 0, "cost": 0.0, "sessions": set()}
        month_stats = {"tokens": 0, "cost": 0.0, "sessions": set()}

        for entry in all_entries:
            timestamp = self._parse_timestamp(entry.get("timestamp", ""))
            tokens = (
                entry.get("input_tokens", 0) +
                entry.get("output_tokens", 0) +
                entry.get("cache_creation_tokens", 0) +
                entry.get("cache_read_tokens", 0)
            )
            cost = entry.get("cost", 0.0)
            session_id = entry.get("session_id", "")

            # 今日统计
            if timestamp >= today_start:
                today_stats["tokens"] += tokens
                today_stats["cost"] += cost
                if session_id:
                    today_stats["sessions"].add(session_id)

            # 本周统计
            if timestamp >= week_start:
                week_stats["tokens"] += tokens
                week_stats["cost"] += cost
                if session_id:
                    week_stats["sessions"].add(session_id)

            # 本月统计
            if timestamp >= month_start:
                month_stats["tokens"] += tokens
                month_stats["cost"] += cost
                if session_id:
                    month_stats["sessions"].add(session_id)

        return {
            "today": {
                "tokens": today_stats["tokens"],
                "cost": today_stats["cost"],
                "sessions": len(today_stats["sessions"]),
            },
            "week": {
                "tokens": week_stats["tokens"],
                "cost": week_stats["cost"],
                "sessions": len(week_stats["sessions"]),
            },
            "month": {
                "tokens": month_stats["tokens"],
                "cost": month_stats["cost"],
                "sessions": len(month_stats["sessions"]),
            },
        }

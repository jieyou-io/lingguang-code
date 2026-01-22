"""
会话管理路由

"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.delete(
    "/v1/sessions/codex/{session_id}",
    summary="删除 Codex 会话",
    description="删除指定的 Codex 会话文件。",
)
async def delete_codex_session(session_id: str):
    """
    删除 Codex 会话

    """
    logger.info("delete_codex_session", session_id=session_id)

    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        raise HTTPException(status_code=404, detail="Sessions directory not found")

    # 递归查找会话文件
    session_file = None
    for file_path in sessions_dir.rglob(f"{session_id}.jsonl"):
        session_file = file_path
        break

    if not session_file or not session_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Session file not found for ID: {session_id}"
        )

    # 删除文件
    try:
        session_file.unlink()
        logger.info("codex_session_deleted", session_id=session_id, path=str(session_file))
        return {"message": f"Successfully deleted session: {session_id}"}
    except OSError as e:
        logger.error("codex_session_delete_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session file: {str(e)}"
        )


@router.delete(
    "/v1/sessions/claude/{project_id}/{session_id}",
    summary="删除 Claude 会话",
    description="删除指定的 Claude 会话文件。",
)
async def delete_claude_session(project_id: str, session_id: str):
    """删除 Claude 会话"""
    logger.info("delete_claude_session", project_id=project_id, session_id=session_id)

    project_dir = Path.home() / ".claude" / "projects" / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    session_file = project_dir / f"{session_id}.jsonl"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session file not found")

    try:
        session_file.unlink()
        logger.info("claude_session_deleted", session_id=session_id)
        return {"message": f"Successfully deleted session: {session_id}"}
    except OSError as e:
        logger.error("claude_session_delete_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

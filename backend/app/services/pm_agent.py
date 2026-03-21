"""
PM Agent — Co-pilot service.

Responsibilities:
- Load pm.md soul as system prompt
- Route memory: detect project references → load ProjectMemory + GlobalMemory
- Stream LLM response via SSE
- Async background update of GlobalMemory after each turn
- Detect intake completion → emit intake_complete event
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncIterator, List, Optional

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat import ChatMessage, GlobalMemory, ProjectMemory
from app.models.project import Project

logger = logging.getLogger(__name__)

SOUL_PATH = os.path.join(os.path.dirname(__file__), "../../souls/pm.md")
MAX_HISTORY_MESSAGES = 20


def _load_soul() -> str:
    try:
        with open(SOUL_PATH, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("pm.md not found at %s", SOUL_PATH)
        return "You are a helpful PM assistant."


async def _get_or_create_global_memory(user_id: str, db: AsyncSession) -> GlobalMemory:
    result = await db.execute(
        select(GlobalMemory).where(GlobalMemory.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        memory = GlobalMemory(user_id=user_id, content="")
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
    return memory


async def _get_or_create_project_memory(project_id: str, db: AsyncSession) -> ProjectMemory:
    result = await db.execute(
        select(ProjectMemory).where(ProjectMemory.project_id == project_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        memory = ProjectMemory(project_id=project_id, content="")
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
    return memory


async def _detect_project_references(
    user_message: str,
    org_id: str,
    db: AsyncSession,
) -> List[Project]:
    result = await db.execute(select(Project).where(Project.org_id == org_id))
    projects = result.scalars().all()
    return [p for p in projects if p.name.lower() in user_message.lower()]


async def _build_system_prompt(
    user_id: str,
    mentioned_projects: List[Project],
    db: AsyncSession,
) -> str:
    soul = _load_soul()

    global_mem = await _get_or_create_global_memory(user_id, db)
    global_section = (
        f"\n\n---\n## 長期記憶（跨專案）\n{global_mem.content}"
        if global_mem.content.strip()
        else ""
    )

    project_sections = ""
    for project in mentioned_projects:
        proj_mem = await _get_or_create_project_memory(str(project.id), db)
        if proj_mem.content.strip():
            project_sections += f"\n\n---\n## 專案記憶：{project.name}\n{proj_mem.content}"

    return soul + global_section + project_sections


async def _load_chat_history(user_id: str, db: AsyncSession) -> List[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def _check_intake_complete(
    conversation: List[dict],
) -> Optional[dict]:
    """
    Ask LLM if the conversation has enough info to create a project.
    Returns {"project_name": str, "project_description": str} or None.
    """
    if len(conversation) < 4:
        # Too short to be a complete intake
        return None

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}" for m in conversation[-10:]
    )

    prompt = (
        "你是一個 intake 完成度判斷員。\n"
        "分析以下對話，判斷 PM agent 是否已完成需求引導並明確提出確認請求。\n\n"
        "完成的條件（全部符合才算）：\n"
        "1. 對話中已識別出清楚的專案名稱或功能名稱\n"
        "2. 目標用戶和核心問題已被提及\n"
        "3. PM agent 已整理摘要並明確詢問用戶確認（例如：「是否符合預期」、「確認後開始執行」）\n\n"
        f"對話記錄：\n{history_text}\n\n"
        "請用 JSON 回覆（不要加任何說明）：\n"
        '{"complete": true/false, "project_name": "...", "project_description": "..."}\n'
        "若 complete 為 false，project_name 和 project_description 填空字串。"
    )

    try:
        response = await litellm.acompletion(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
            api_key=settings.llm_api_key,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if data.get("complete") and data.get("project_name"):
            return {
                "project_name": data["project_name"],
                "project_description": data.get("project_description", ""),
            }
    except Exception as exc:
        logger.warning("Intake check failed: %s", exc)

    return None


async def _update_global_memory_background(
    user_id: str,
    user_message: str,
    assistant_reply: str,
    current_memory: str,
) -> None:
    try:
        prompt = (
            "你是一個記憶管理員。根據以下對話，更新使用者的長期記憶摘要。"
            "保留重要的偏好、決策和跨專案知識。控制在 500 字以內。\n\n"
            f"現有記憶：\n{current_memory or '（無）'}\n\n"
            f"新對話：\nUser: {user_message}\nAssistant: {assistant_reply}\n\n"
            "更新後的記憶摘要："
        )
        response = await litellm.acompletion(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
            api_key=settings.llm_api_key,
        )
        new_memory = response.choices[0].message.content

        from app.db.base import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(GlobalMemory).where(GlobalMemory.user_id == user_id)
            )
            mem = result.scalar_one_or_none()
            if mem:
                mem.content = new_memory
                await db.commit()
    except Exception as exc:
        logger.warning("Failed to update global memory: %s", exc)


async def stream_pm_response(
    user_id: str,
    org_id: str,
    user_message: str,
    db: AsyncSession,
    intake_already_triggered: bool = False,
) -> AsyncIterator[str]:
    """
    Stream PM Agent response as SSE events.
    Yields strings: "data: <json>\n\n"

    SSE event types:
      delta             — text chunk
      done              — stream finished, includes project_context_ids
      intake_complete   — PM has completed intake, includes project_name/description
      error             — error message
    """
    mentioned_projects = await _detect_project_references(user_message, org_id, db)
    project_context_ids = [str(p.id) for p in mentioned_projects]

    system_prompt = await _build_system_prompt(user_id, mentioned_projects, db)
    history = await _load_chat_history(user_id, db)

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    # Persist user message
    user_msg = ChatMessage(
        user_id=user_id,
        role="user",
        content=user_message,
        project_context_ids=project_context_ids,
    )
    db.add(user_msg)
    await db.commit()

    # Stream LLM response
    full_reply = ""
    try:
        stream = await litellm.acompletion(
            model=settings.llm_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            api_key=settings.llm_api_key,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_reply += delta
                yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"

    except Exception as exc:
        error_msg = f"PM Agent 發生錯誤：{exc}"
        logger.error("PM Agent stream error: %s", exc)
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        full_reply = error_msg

    # Persist assistant reply
    assistant_msg = ChatMessage(
        user_id=user_id,
        role="assistant",
        content=full_reply,
        project_context_ids=project_context_ids,
    )
    db.add(assistant_msg)
    await db.commit()

    # Build updated conversation for intake check
    updated_history = [*history, {"role": "user", "content": user_message}, {"role": "assistant", "content": full_reply}]

    yield f"data: {json.dumps({'type': 'done', 'project_context_ids': project_context_ids})}\n\n"

    # Background tasks (non-blocking)
    global_mem = await _get_or_create_global_memory(user_id, db)
    asyncio.create_task(
        _update_global_memory_background(user_id, user_message, full_reply, global_mem.content)
    )

    # Intake completion check (only if not already triggered)
    if not intake_already_triggered:
        intake_result = await _check_intake_complete(updated_history)
        if intake_result:
            yield f"data: {json.dumps({'type': 'intake_complete', **intake_result})}\n\n"

"""N09 场次拆分Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import (
    ChunkRepository, CharacterRepository, OutlineRepository,
)
from src.utils.logger import node_logger


class SceneSplitterAgent(AgentBase):
    """场次拆分Agent — N09 单集场次拆分

    将单集大纲拆分为15-25场可执行的场景卡片。
    """

    node_id = "N09"
    node_name = "场次拆分Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.5)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/08_scene_splitter.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, episode_id: str = "EP01") -> dict:
        """拆分单集为场次

        Returns:
            {episode_id, total_scenes, scenes: list[dict]}
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            log.info(f"加载分集大纲: {episode_id}")
            context = self._load_context(project_id, episode_id)

            if self.prompt_template:
                scenes = self._llm_split(context)
            else:
                scenes = self._template_split(context)

            self._save_scenes(project_id, episode_id, scenes)

            log.info(f"场次拆分完成: {len(scenes)} 场")

        return {"episode_id": episode_id, "total_scenes": len(scenes), "scenes": scenes}

    def _load_context(self, project_id: str, episode_id: str) -> dict:
        """加载上下文"""
        context = {"episode_id": episode_id, "project_id": project_id}

        # 加载分集大纲
        outline_path = Path("workspace/projects") / project_id / "work" / "outlines" / f"{episode_id}.json"
        if outline_path.exists():
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            context["episode_summary"] = outline.get("summary", "")
            context["episode_number"] = outline.get("episode_number", 1)
            context["core_conflict"] = outline.get("core_conflict", "")

        # 加载人物
        with get_session() as session:
            char_repo = CharacterRepository(session)
            chars = char_repo.list_by_project(project_id)
            context["characters"] = [{"id": c.char_id, "name": c.name, "personality": c.core_personality} for c in chars[:10]]

            chunk_repo = ChunkRepository(session)
            chunks = chunk_repo.list_by_project(project_id)
            context["chunks"] = [{"id": c.chunk_id, "chapter": c.chapter, "summary": c.summary[:200]} for c in chunks[:10]]

        return context

    def _llm_split(self, context: dict) -> list[dict]:
        """LLM 场次拆分"""
        prompt = f"""将第{context.get('episode_number', 1)}集大纲拆分为15-25场戏。

## 本集信息
- 核心冲突: {context.get('core_conflict', '')}
- 摘要: {context.get('episode_summary', '')[:500]}

## 可用的原著语义块
{json.dumps(context.get('chunks', []), ensure_ascii=False, indent=2)[:1500]}

## 出场人物
{json.dumps(context.get('characters', []), ensure_ascii=False, indent=2)[:1000]}

输出完整的JSON格式场次清单。
"""

        try:
            response = self.call_llm(user_input=prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("scenes", [])
        except Exception as e:
            node_logger.warn(f"LLM 场次拆分失败: {e}")

        return self._template_split(context)

    def _template_split(self, context: dict) -> list[dict]:
        """模板拆分（降级方案）：生成5场基础结构"""
        ep_id = context["episode_id"]
        chars = context.get("characters", [])
        main_char = chars[0]["name"] if chars else "主角"
        chunk_ids = [c["id"] for c in context.get("chunks", [])]

        template_scenes = [
            {
                "scene_id": f"{ep_id}-SC01",
                "scene_number": 1,
                "episode_id": ep_id,
                "narrative_function": "推进剧情",
                "core_info_increment": "建立本集核心情境与冲突",
                "characters_in_scene": [c["id"] for c in chars[:2]],
                "scene_location": "待设定",
                "scene_time": "日",
                "opening": f"承接上集结尾，{main_char}面临新的挑战",
                "development": "核心冲突初步展现",
                "climax": "第一个转折点",
                "closing": "引出下一场",
                "source_chapter": "",
                "source_chunk_ids": chunk_ids[:1],
                "estimated_duration_min": 2.5,
                "status": "pending",
            },
            {
                "scene_id": f"{ep_id}-SC02",
                "scene_number": 2,
                "episode_id": ep_id,
                "narrative_function": "塑造人物",
                "core_info_increment": f"展示{main_char}的性格特质与行为模式",
                "characters_in_scene": [c["id"] for c in chars[:3]],
                "scene_location": "待设定",
                "scene_time": "日",
                "opening": "承接SC01结尾",
                "development": "人物关系推进",
                "climax": "人物性格展现",
                "closing": "过渡到下一场",
                "source_chapter": "",
                "source_chunk_ids": chunk_ids[:1],
                "estimated_duration_min": 2.0,
                "status": "pending",
            },
            {
                "scene_id": f"{ep_id}-SC03",
                "scene_number": 3,
                "episode_id": ep_id,
                "narrative_function": "制造冲突",
                "core_info_increment": "冲突升级，推动剧情转折",
                "characters_in_scene": [c["id"] for c in chars[:2]],
                "scene_location": "待设定",
                "scene_time": "日",
                "opening": "承接SC02结尾",
                "development": "对抗升级",
                "climax": "关键对决/冲突爆发",
                "closing": "留悬念",
                "source_chapter": "",
                "source_chunk_ids": chunk_ids[:1],
                "estimated_duration_min": 3.0,
                "status": "pending",
            },
        ]

        return template_scenes

    def _save_scenes(self, project_id: str, episode_id: str, scenes: list[dict]):
        """保存场次清单"""
        output_dir = Path("workspace/projects") / project_id / "work" / "scene_cards"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{episode_id}_scenes.json").write_text(
            json.dumps({"episode_id": episode_id, "total_scenes": len(scenes), "scenes": scenes},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

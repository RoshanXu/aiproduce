"""N09 场次拆分Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import (
    ChunkRepository, CharacterRepository, OutlineRepository,
    WorldRepository, TimelineRepository,
)
from src.utils.logger import node_logger


class SceneSplitterAgent(AgentBase):
    """场次拆分Agent — N09 单集场次拆分

    将单集大纲拆分为15-25场可执行的场景卡片。
    """

    node_id = "N09"
    node_name = "场次拆分Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.5, max_tokens=16384)
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

            scenes = self._llm_split(context)

            self._save_scenes(project_id, episode_id, scenes)

            log.info(f"场次拆分完成: {len(scenes)} 场")

        return {"episode_id": episode_id, "total_scenes": len(scenes), "scenes": scenes}

    def _load_context(self, project_id: str, episode_id: str) -> dict:
        """加载上下文，包括人物、世界观、时间线"""
        context = {"episode_id": episode_id, "project_id": project_id}

        # 加载分集大纲
        outline_path = Path("workspace/projects") / project_id / "work" / "outlines" / f"{episode_id}.json"
        if outline_path.exists():
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            context["episode_summary"] = outline.get("summary", "")
            context["episode_number"] = outline.get("episode_number", 1)
            context["core_conflict"] = outline.get("core_conflict", "")
            context["ending_hook"] = outline.get("ending_hook", "")
            context["character_states_end"] = outline.get("character_states_end", {})
            context["foreshadow_planted"] = outline.get("foreshadow_planted", [])

        # 加载前集大纲（用于连续性衔接）
        if episode_id != "EP01":
            prev_ep_num = int(episode_id.replace("EP", "")) - 1
            prev_path = Path("workspace/projects") / project_id / "work" / "outlines" / f"EP{prev_ep_num:02d}.json"
            if prev_path.exists():
                prev = json.loads(prev_path.read_text(encoding="utf-8"))
                context["prev_episode_summary"] = prev.get("summary", "")
                context["prev_ending_hook"] = prev.get("ending_hook", "")
                context["prev_character_states"] = prev.get("character_states_end", {})

        with get_session() as session:
            # 人物
            char_repo = CharacterRepository(session)
            chars = char_repo.list_by_project(project_id)
            context["characters"] = [
                {"id": c.char_id, "name": c.name, "personality": c.core_personality,
                 "speech_style": c.speech_style or "", "core_identity": c.core_identity or ""}
                for c in chars[:10]
            ]

            # 世界观场景
            world_repo = WorldRepository(session)
            world_records = world_repo.list_by_project(project_id)
            world_scenes = []
            for wr in world_records[:1]:
                aj = wr.asset_json or {}
                for s in aj.get("core_scenes", [])[:10]:
                    world_scenes.append({
                        "name": s.get("scene_name", ""),
                        "type": s.get("space_type", ""),
                        "features": s.get("visual_features", ""),
                        "function": s.get("core_function", ""),
                    })
            context["world_scenes"] = world_scenes

            # 时间线
            timeline_repo = TimelineRepository(session)
            tl_records = timeline_repo.list_by_project(project_id)
            context["foreshadows"] = []
            for tl in tl_records[:1]:
                aj = tl.asset_json or {}
                for f in aj.get("foreshadow_table", []):
                    context["foreshadows"].append({
                        "id": f.get("foreshadow_id", ""),
                        "plant": f.get("plant_content", ""),
                        "status": f.get("status", "pending"),
                    })

            # 语义块
            chunk_repo = ChunkRepository(session)
            chunks = chunk_repo.list_by_project(project_id)
            context["chunks"] = [{"id": c.chunk_id, "chapter": c.chapter, "summary": c.summary[:200]} for c in chunks[:10]]

        return context

    def _llm_split(self, context: dict) -> list[dict]:
        """LLM 场次拆分 — 注入世界观场景和连续性约束"""
        ep_id = context.get("episode_id", "EP01")
        ep_num = context.get("episode_number", 1)

        # 世界观可用场景
        world_locations = ""
        for ws in context.get("world_scenes", []):
            world_locations += f"  - {ws['name']} ({ws.get('type','')}): {ws.get('features','')} — {ws.get('function','')}\n"

        # 前集衔接信息
        prev_info = ""
        if context.get("prev_episode_summary"):
            prev_info = f"""## 前集结尾（本集开场必须衔接）
- 前集概要: {context.get('prev_episode_summary', '')[:300]}
- 前集结尾钩子: {context.get('prev_ending_hook', '')}
- 前集结束时的角色状态: {json.dumps(context.get('prev_character_states', {}), ensure_ascii=False)}
"""

        # 待回收伏笔
        foreshadows_text = ""
        for f in context.get("foreshadows", []):
            if f.get("status") == "pending":
                foreshadows_text += f"  - [{f['id']}] {f['plant']}\n"

        prompt = f"""将第{ep_num}集大纲拆分为15-25场戏。

## 本集信息
- 核心冲突: {context.get('core_conflict', '')}
- 摘要: {context.get('episode_summary', '')[:500]}
- 结尾钩子: {context.get('ending_hook', '')}
{prev_info}
## 本集待埋设/回收的伏笔
{foreshadows_text or '（无特定伏笔要求）'}

## 世界观可用场景（优先使用已设定场景）
{world_locations or '（无预设定场景，根据剧情创建）'}

## 出场人物（性格/语言风格必须一致）
{json.dumps(context.get('characters', []), ensure_ascii=False, indent=2)[:1000]}

## 可用的原著语义块
{json.dumps(context.get('chunks', []), ensure_ascii=False, indent=2)[:1000]}

## 硬性约束
1. 第1场必须承接前集结尾钩子
2. 场景地点优先从世界观已设定场景中选择
3. narrative_function 必须从六分类中选择
4. 每场的 closing 必须自然衔接到下一场的 opening

输出JSON格式（仅JSON）：
{{
  "scenes": [
    {{
      "scene_id": "{ep_id}-SC01",
      "scene_number": 1,
      "episode_id": "{ep_id}",
      "narrative_function": "推进剧情|塑造人物|铺垫伏笔|制造冲突|过渡衔接|情绪释放",
      "core_info_increment": "本场观众知道的新信息",
      "characters_in_scene": ["CHAR-001"],
      "scene_location": "具体地点（优先使用已设定场景）",
      "scene_time": "日|夜|晨|暮",
      "opening": "开场状态（第1场须衔接前集钩子）",
      "development": "发展过程",
      "climax": "本场高潮",
      "closing": "收尾状态与钩子",
      "source_chapter": "对应原著章节",
      "source_chunk_ids": ["CHUNK-0001"],
      "estimated_duration_min": 2.5
    }}
  ]
}}"""

        response = self.call_llm(user_input=prompt)
        data = self._parse_json_response(response)
        scenes = data.get("scenes", [])
        if not scenes:
            raise RuntimeError("LLM 场次拆分返回空 scenes 列表")
        # 校验每场必须有 scene_id
        for i, s in enumerate(scenes):
            if "scene_id" not in s:
                ep_id = context.get("episode_id", "EP01")
                s["scene_id"] = f"{ep_id}-SC{i+1:02d}"
        return scenes

    def _save_scenes(self, project_id: str, episode_id: str, scenes: list[dict]):
        """保存场次清单"""
        output_dir = Path("workspace/projects") / project_id / "work" / "scene_cards"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{episode_id}_scenes.json").write_text(
            json.dumps({"episode_id": episode_id, "total_scenes": len(scenes), "scenes": scenes},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

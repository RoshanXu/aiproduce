"""N03 世界观资产管理Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import WorldRepository, ChunkRepository
from src.db.models import WorldRecord
from src.utils.logger import node_logger


class WorldAssetAgent(AgentBase):
    """世界观资产管理Agent

    负责 N03/N06：从语义块标签聚合世界观资产库。
    """

    node_id = "N03"
    node_name = "世界观资产管理Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.3)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/04_world_asset.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str) -> dict:
        """从语义块标签聚合世界观资产库"""
        with node_logger.node_context(self.node_id, self.node_name) as log:
            log.info("加载语义块标签...")
            with get_session() as session:
                chunk_repo = ChunkRepository(session)
                chunks = chunk_repo.list_by_project(project_id)

            if not chunks:
                log.warning("无语义块数据")
                return {"world": {}}

            # 聚合世界观细节标签
            world_details = []
            locations: dict[str, int] = {}
            for chunk in chunks:
                tags = chunk.tags_json or {}
                wd = tags.get("world_details", "")
                if wd and wd not in ("无", "待提取"):
                    world_details.append(wd)
                loc = tags.get("location", "")
                if loc and loc not in ("无", "待定位", "待提取"):
                    locations[loc] = locations.get(loc, 0) + 1

            # 构建场景资产
            core_scenes = []
            for scene_name, count in sorted(locations.items(), key=lambda x: -x[1]):
                if count >= 1:  # 原型阶段，所有地点都建为场景
                    core_scenes.append({
                        "scene_id": f"SCENE-{len(core_scenes)+1:03d}",
                        "scene_name": scene_name,
                        "space_type": "待补充",
                        "visual_features": "待补充",
                        "appearance_chapters": [],
                        "core_function": "待补充",
                    })

            # 尝试用 LLM 做深度世界观构建
            if self.prompt_template and world_details:
                world = self._llm_build_world(world_details, core_scenes)
            else:
                world = self._rule_based_build(world_details, core_scenes)

            # 存储
            self._store_world(project_id, world)

            log.info(f"世界观资产库构建完成: {len(core_scenes)} 个核心场景")

        return {"world": world}

    def _llm_build_world(self, world_details: list[str], core_scenes: list[dict]) -> dict:
        """使用 LLM 做深度世界观构建"""
        details_text = "\n".join(f"- {d}" for d in world_details[:20])

        prompt = f"""基于以下世界观细节碎片，构建结构化世界观资产。

世界观细节：
{details_text}

核心场景：
{json.dumps(core_scenes[:10], ensure_ascii=False, indent=2)}

请输出 JSON（仅 JSON，不要其他文字）：
{{
  "basic_settings": {{
    "era_background": "时代背景",
    "geography": "地理疆域",
    "core_factions": ["势力1"],
    "social_hierarchy": "社会阶层",
    "universal_rules": "通用规则"
  }},
  "culture_details": {{
    "costume_rules": "服饰规制（无则'待补充'）",
    "food_and_items": "饮食器物（无则'待补充'）",
    "etiquette_and_titles": "礼仪称谓",
    "customs_and_institutions": "习俗制度（无则'待补充'）"
  }},
  "core_scenes": {json.dumps(core_scenes[:5], ensure_ascii=False)},
  "setting_confidence": {{
    "explicit": ["原著明确设定1"],
    "inferred": ["推断设定1（标注依据）"],
    "historical_reference": ["历史参照1"]
  }}
}}"""

        try:
            response = self.call_llm(user_input=prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            node_logger.warn(f"LLM 世界观构建失败: {e}")

        return self._rule_based_build(world_details, core_scenes)

    def _rule_based_build(self, world_details: list[str], core_scenes: list[dict]) -> dict:
        """降级方案"""
        return {
            "basic_settings": {
                "era_background": "待补充（基于原文分析）",
                "geography": "待补充",
                "core_factions": [],
                "social_hierarchy": "待补充",
                "universal_rules": "待补充",
            },
            "culture_details": {
                "costume_rules": "待补充",
                "food_and_items": "待补充",
                "etiquette_and_titles": "；".join(world_details[:5]) if world_details else "待补充",
                "customs_and_institutions": "待补充",
            },
            "core_scenes": core_scenes,
            "setting_confidence": {
                "explicit": [],
                "inferred": [],
                "historical_reference": [],
            },
        }

    def _store_world(self, project_id: str, world: dict):
        """存储世界观资产"""
        with get_session() as session:
            repo = WorldRepository(session)
            record = WorldRecord(
                world_id="WORLD-001",
                project_id=project_id,
                era_background=world.get("basic_settings", {}).get("era_background", ""),
                geography=world.get("basic_settings", {}).get("geography", ""),
                asset_json=world,
                version="1.0",
            )
            repo.create(record)

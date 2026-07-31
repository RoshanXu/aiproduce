"""N03 时间线管理Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import TimelineRepository, ChunkRepository
from src.db.models import TimelineRecord
from src.utils.logger import node_logger


class TimelineAssetAgent(AgentBase):
    """时间线管理Agent

    负责 N03/N06：从语义块标签构建全局时间轴与伏笔回收表。
    """

    node_id = "N03"
    node_name = "时间线管理Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.3)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/05_timeline_asset.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str) -> dict:
        """从语义块标签构建时间线与伏笔表"""
        with node_logger.node_context(self.node_id, self.node_name) as log:
            log.info("加载语义块数据...")
            with get_session() as session:
                chunk_repo = ChunkRepository(session)
                chunks = chunk_repo.list_by_project(project_id)

            if not chunks:
                log.warning("无语义块数据")
                return {"timeline": {}}

            # 聚合事件信息
            events = []
            foreshadows = []
            for chunk in chunks:
                tags = chunk.tags_json or {}
                key_events = tags.get("key_events", "")
                foreshadow = tags.get("foreshadow", "")

                if key_events and key_events not in ("无", "待提取", "日常/过渡"):
                    events.append({
                        "event_id": f"EVT-{len(events)+1:03d}",
                        "time_point": f"第{chunk.chapter}章",
                        "time_confidence": "exact",
                        "event_description": key_events,
                        "involved_characters": chunk.core_characters_json or [],
                        "location": tags.get("location", ""),
                        "event_impact": "待补充",
                        "source_chunk_id": chunk.chunk_id,
                    })

                if foreshadow and foreshadow not in ("无", "待提取"):
                    foreshadows.append({
                        "foreshadow_id": f"FOR-{len(foreshadows)+1:03d}",
                        "plant_chapter": chunk.chapter,
                        "plant_content": foreshadow,
                        "payoff_chapter": None,
                        "payoff_method": None,
                        "status": "pending",
                        "source_chunk_id": chunk.chunk_id,
                    })

            # LLM 深度分析
            timeline = self._llm_build_timeline(events, foreshadows)

            # 存储
            self._store_timeline(project_id, timeline)

            log.info(f"时间线构建完成: {len(events)} 个事件, {len(foreshadows)} 个伏笔")

        return {"timeline": timeline}

    def _llm_build_timeline(self, events: list[dict], foreshadows: list[dict]) -> dict:
        """LLM 深度时间线分析"""
        prompt = f"""基于以下事件列表，构建完整时间线与伏笔回收对照表。

事件列表：
{json.dumps(events[:20], ensure_ascii=False, indent=2)}

已识别的伏笔线索：
{json.dumps(foreshadows[:10], ensure_ascii=False, indent=2)}

请输出 JSON（仅 JSON）：
{{
  "main_timeline": {json.dumps(events[:15], ensure_ascii=False)},
  "sub_timelines": {{}},
  "foreshadow_table": {json.dumps(foreshadows[:10], ensure_ascii=False)}
}}

要求：
1. 对每个事件标注 time_confidence: exact/estimated/fuzzy
2. 尝试将模糊时间段事件标注估计区间
3. 检查是否有明显的时间悖论或因果倒置
"""

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    def _store_timeline(self, project_id: str, timeline: dict):
        """存储时间线资产"""
        with get_session() as session:
            repo = TimelineRepository(session)
            record = TimelineRecord(
                timeline_id="TL-001",
                project_id=project_id,
                asset_json=timeline,
                version="1.0",
            )
            repo.create(record)

"""N13 时间线与伏笔校验Agent"""

import json
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import TimelineRepository
from src.utils.logger import node_logger


class TimelineCheckerAgent(AgentBase):
    """时间线与伏笔校验Agent — N13

    校验剧本的时间逻辑与伏笔一致性。
    """

    node_id = "N13"
    node_name = "时间线与伏笔校验Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.2)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/11_timeline_checker.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, scene_id: str) -> dict:
        """校验单场剧本的时间线合规性（LLM 语义驱动）"""
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 加载时间线资产
            with get_session() as session:
                timeline_repo = TimelineRepository(session)
                tl_records = timeline_repo.list_by_project(project_id)
                timeline_data = {}
                for tl in tl_records[:1]:
                    timeline_data = tl.asset_json or {}

            # 加载剧本
            script_path = Path("workspace/projects") / project_id / "work" / "drafts" / f"{scene_id}.json"
            script = {}
            if script_path.exists():
                script = json.loads(script_path.read_text(encoding="utf-8"))

            # 加载前后场次剧本（用于连续性检查）
            prev_script = self._load_adjacent_script(project_id, scene_id, offset=-1)
            next_script = self._load_adjacent_script(project_id, scene_id, offset=1)

            # LLM 语义校验
            report = self._llm_check(script, prev_script, next_script, timeline_data, scene_id)

            # 保存
            self._save_report(project_id, scene_id, report)

            log.info(f"时间线校验: {report.get('verdict', '?')}")

        return report

    def _load_adjacent_script(self, project_id: str, scene_id: str, offset: int) -> dict:
        """加载相邻场次剧本"""
        parts = scene_id.rsplit("-SC", 1) if "-SC" in scene_id else scene_id.rsplit("-", 1)
        if len(parts) == 2:
            try:
                adj_num = int(parts[1]) + offset
                if adj_num >= 1:
                    adj_id = f"{parts[0]}-SC{adj_num:02d}"
                    adj_path = Path("workspace/projects") / project_id / "work" / "drafts" / f"{adj_id}.json"
                    if adj_path.exists():
                        return json.loads(adj_path.read_text(encoding="utf-8"))
            except (ValueError, IndexError):
                pass
        return {}

    def _llm_check(self, script: dict, prev_script: dict, next_script: dict,
                   timeline: dict, scene_id: str) -> dict:
        """LLM 时间线与连续性语义校验"""
        body_text = json.dumps(script.get("body", []), ensure_ascii=False, indent=2)[:2000]
        meta = script.get("meta", {})

        # 前场信息
        prev_info = ""
        if prev_script:
            pmeta = prev_script.get("meta", {})
            prev_info = (
                f"前场ID: {pmeta.get('scene_id','?')} | 地点: {pmeta.get('scene_location','?')}\n"
                f"前场结尾: {json.dumps(prev_script.get('body', [])[-2:], ensure_ascii=False)[:500]}\n"
            )

        # 时间线摘要
        main_tl = timeline.get("main_timeline", [])
        tl_summary = ""
        for e in main_tl[:10]:
            tl_summary += f"  - {e.get('time_point','')}: {e.get('event_description','')}\n"

        # 伏笔表
        foreshadow_text = ""
        for f in timeline.get("foreshadow_table", []):
            foreshadow_text += (
                f"  - [{f.get('foreshadow_id','')}] {f.get('plant_content','')}\n"
                f"    埋设: 第{f.get('plant_chapter','?')}章 | 状态: {f.get('status','pending')}\n"
            )

        prompt = f"""严格校验以下场次的时间线、伏笔和跨场连续性。每项违规必须标记 severity。

## 原著时间线
{tl_summary or '（无预存时间线）'}

## 伏笔对照表
{foreshadow_text or '（无预存伏笔）'}

## 前场结尾（连续性检查基准）
{prev_info or '（本场为第一场，无前场）'}

## 本场剧本
场次ID: {scene_id}
场景地点: {meta.get('scene_location','?')} | 场景时间: {meta.get('scene_time','?')}
{body_text}

## 五维校验标准
1. **时间连续性**：本场时间与前场结尾是否连续？时间跳跃是否有明确说明？
2. **空间连续性**：本场地点变化是否合理？前场在A地结尾，本场开场在B地，中间是否有转场？
3. **因果连续性**：本场事件是否由前场事件自然推动？是否存在因果断裂？
4. **伏笔埋设/回收**：本场是否涉及已有伏笔的回收？是否有新伏笔需要标记？伏笔回收是否与原设一致？
5. **时间线一致性**：本场描述的时间信息是否与原著时间线一致？是否存在时间悖论？

输出JSON（仅JSON）：
{{
  "scene_id": "{scene_id}",
  "verdict": "PASS | NEEDS_REVISION | NEEDS_REWRITE",
  "blocking_issues": [
    {{"type": "causality_break|time_conflict|foreshadow_error|continuity_gap", "detail": "具体描述和剧本原文引用", "expected": "应该怎样", "severity": "blocking"}}
  ],
  "warning_issues": [
    {{"type": "...", "detail": "轻微问题描述", "suggestion": "建议修改", "severity": "warning"}}
  ],
  "continuity_check": {{
    "time_continuous": true,
    "space_continuous": true,
    "causality_continuous": true,
    "continuity_notes": "连续性总结"
  }},
  "foreshadow_check": {{
    "resolved_in_scene": ["本场回收的伏笔ID"],
    "planted_in_scene": ["本场新埋的伏笔描述"],
    "still_pending": ["仍待回收的伏笔ID"],
    "consistency_issues": ["伏笔一致性问题"]
  }},
  "timeline_alignment": {{
    "original_event_matched": "本场匹配的原著事件（无则null）",
    "deviation_note": "偏离原著的说明（无则null）"
  }}
}}"""

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    def _save_report(self, project_id: str, scene_id: str, report: dict):
        output_dir = Path("workspace/projects") / project_id / "work" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}_timeline_check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

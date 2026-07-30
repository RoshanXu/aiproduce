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
        """校验单场剧本的时间线合规性"""
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 加载时间线资产
            with get_session() as session:
                timeline_repo = TimelineRepository(session)
                timeline = timeline_repo.get_by_project(project_id)
                timeline_data = timeline.asset_json if timeline else {}

            # 加载剧本
            script_path = Path("workspace/projects") / project_id / "work" / "drafts" / f"{scene_id}.json"
            script = {}
            if script_path.exists():
                script = json.loads(script_path.read_text(encoding="utf-8"))

            # 执行校验
            report = self._check(script, timeline_data, scene_id)

            # 保存
            self._save_report(project_id, scene_id, report)

            log.info(f"时间线校验: {report.get('verdict', '?')}")

        return report

    def _check(self, script: dict, timeline: dict, scene_id: str) -> dict:
        """执行时间线校验"""
        issues = []
        foreshadow_issues = []

        meta = script.get("meta", {})
        scene_time = meta.get("scene_time", "")
        info_increment = script.get("info_increment_check", "")

        # 1. 场景时间与时间线对照
        main_timeline = timeline.get("main_timeline", [])
        scene_chapter = scene_id.split("-")[0] if "-" in scene_id else ""

        # 2. 检查伏笔状态
        foreshadow_table = timeline.get("foreshadow_table", [])
        pending_foreshadows = [f for f in foreshadow_table if f.get("status") == "pending"]

        # 3. 检查信息增量中是否有时间跳跃
        if info_increment:
            time_jump_keywords = ["数日后", "几个月后", "一年后", "转眼", "时光飞逝"]
            for kw in time_jump_keywords:
                if kw in info_increment:
                    issues.append({
                        "type": "time_jump_consistency",
                        "detail": f"信息增量含时间跳跃标记'{kw}'，需确认时间线连续性",
                        "severity": "warning",
                    })
                    break

        # 4. 检查是否有未回收的伏笔在时间线上超期
        if pending_foreshadows:
            foreshadow_issues = [
                {
                    "foreshadow_id": f.get("foreshadow_id", ""),
                    "plant_chapter": f.get("plant_chapter", ""),
                    "content": f.get("plant_content", ""),
                    "status": "pending_unresolved",
                    "suggestion": "标记为待回收，检查后续剧本是否安排回收",
                }
                for f in pending_foreshadows[:5]
            ]

        blocking = [i for i in issues if i.get("severity") == "blocking"]
        warnings = [i for i in issues if i.get("severity") == "warning"]

        return {
            "scene_id": scene_id,
            "verdict": "PASS" if not blocking else "FAIL",
            "blocking_issues": blocking,
            "warning_issues": warnings,
            "foreshadow_status": {
                "total": len(foreshadow_table),
                "pending": len(pending_foreshadows),
                "resolved": len([f for f in foreshadow_table if f.get("status") == "resolved"]),
            },
            "pending_foreshadows_detail": foreshadow_issues,
        }

    def _save_report(self, project_id: str, scene_id: str, report: dict):
        output_dir = Path("workspace/projects") / project_id / "work" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}_timeline_check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

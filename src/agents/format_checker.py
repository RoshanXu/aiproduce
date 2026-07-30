"""N14 格式与合规校验Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.utils.logger import node_logger


class FormatCheckerAgent(AgentBase):
    """格式与合规校验Agent — N14

    校验剧本格式规范与基础合规性。
    """

    node_id = "N14"
    node_name = "格式与合规校验Agent"

    # 禁用词汇列表（以古装剧为例，可配置）
    FORBIDDEN_WORDS = [
        "突然", "竟然", "原来如此", "似乎", "仿佛",
        "氛围", "气氛", "感觉", "心情",
        "OK", "好的", "没问题",  # 现代口语
        "手机", "电脑", "网络",  # 穿越物品
    ]

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.1)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/12_format_checker.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, scene_id: str) -> dict:
        """校验单场剧本格式合规性"""
        with node_logger.node_context(self.node_id, self.node_name) as log:
            script_path = Path("workspace/projects") / project_id / "work" / "drafts" / f"{scene_id}.json"
            if not script_path.exists():
                return {"scene_id": scene_id, "verdict": "SKIP"}

            script = json.loads(script_path.read_text(encoding="utf-8"))

            report = self._check(script, scene_id)
            self._save_report(project_id, scene_id, report)

            log.info(f"格式校验: {report['verdict']} (格式:{report['format_errors']}, 禁用词:{report['forbidden_word_count']})")

        return report

    def _check(self, script: dict, scene_id: str) -> dict:
        """执行格式与合规校验"""
        format_errors = []
        forbidden_hits = []

        body = script.get("body", [])

        # 1. 格式检查
        meta = script.get("meta", {})
        if not meta.get("scene_id"):
            format_errors.append("缺少 scene_id")
        if not meta.get("scene_location"):
            format_errors.append("缺少 scene_location")
        if not meta.get("scene_time"):
            format_errors.append("缺少 scene_time")

        scene_desc = script.get("scene_description", {})
        if not scene_desc.get("content"):
            format_errors.append("缺少场景描写")

        # 检查正文格式
        action_count = 0
        dialogue_count = 0
        performance_notes = 0
        total_char_count = 0

        for item in body:
            prefix = item.get("prefix", "")
            content = item.get("content", "")

            if prefix == "▲":
                action_count += 1
                total_char_count += len(content)
            elif "character" in item:
                dialogue_count += 1
                total_char_count += len(content)
            if prefix == "◎":
                performance_notes += 1

            # 检查禁用词汇
            for word in self.FORBIDDEN_WORDS:
                if word in content:
                    forbidden_hits.append({
                        "word": word,
                        "location": item.get("character", prefix),
                        "context": content[:80],
                    })

        # 2. 格式指标检查
        if action_count == 0:
            format_errors.append("无动作描写（▲）")
        if dialogue_count == 0 and action_count > 3:
            format_errors.append("有动作但无台词，检查是否为纯动作场景")
        if performance_notes > 5:
            format_errors.append(f"表演提示过多（{performance_notes}>5）")

        # 3. 台词占比检查
        dialogue_chars = sum(
            len(item.get("content", ""))
            for item in body if "character" in item
        )
        if total_char_count > 0:
            dialogue_ratio = dialogue_chars / total_char_count
            if dialogue_ratio < 0.3 and dialogue_count > 0:
                format_errors.append(f"台词占比偏低（{dialogue_ratio:.0%}<30%）")

        # 4. 转场检查
        transition = script.get("transition", {})
        if not transition.get("transition_type"):
            format_errors.append("缺少转场标记（★）")

        # 5. 自检字段
        if not script.get("info_increment_check"):
            format_errors.append("缺少信息增量自检")

        blocking = [e for e in format_errors if "缺少" in e]
        warnings = [e for e in format_errors if "缺少" not in e]

        return {
            "scene_id": scene_id,
            "verdict": "PASS" if not blocking else "FAIL",
            "format_errors": len(format_errors),
            "blocking_issues": [{"type": "format", "detail": e, "severity": "blocking"} for e in blocking],
            "warning_issues": [{"type": "format", "detail": e, "severity": "warning"} for e in warnings],
            "forbidden_word_count": len(forbidden_hits),
            "forbidden_word_hits": forbidden_hits[:10],
            "metrics": {
                "action_count": action_count,
                "dialogue_count": dialogue_count,
                "performance_notes": performance_notes,
                "total_char_count": total_char_count,
                "dialogue_ratio": round(dialogue_chars / total_char_count, 2) if total_char_count > 0 else 0,
            },
        }

    def _save_report(self, project_id: str, scene_id: str, report: dict):
        output_dir = Path("workspace/projects") / project_id / "work" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}_format_check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

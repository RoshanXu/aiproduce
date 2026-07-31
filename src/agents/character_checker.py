"""N12 人设一致性校验Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import CharacterRepository
from src.utils.logger import node_logger


class CharacterCheckerAgent(AgentBase):
    """人设一致性校验Agent — N12 人设校验

    对比剧本与人物资产库，输出分级校验报告。
    """

    node_id = "N12"
    node_name = "人设一致性校验Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.2)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/10_character_checker.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, scene_id: str) -> dict:
        """校验单场剧本人设一致性

        Returns:
            {scene_id, verdict, blocking_issues, warning_issues, ...}
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 加载剧本
            script_path = Path("workspace/projects") / project_id / "work" / "drafts" / f"{scene_id}.json"
            if not script_path.exists():
                log.warning(f"剧本不存在: {scene_id}")
                return {"scene_id": scene_id, "verdict": "SKIP", "reason": "script not found"}

            script = json.loads(script_path.read_text(encoding="utf-8"))

            # 加载人物资产
            with get_session() as session:
                char_repo = CharacterRepository(session)
                meta = script.get("meta", {})
                char_names_str = meta.get("characters_in_scene", "")
                char_names = [n.strip() for n in char_names_str.split(",") if n.strip()]

                char_profiles = {}
                for char in char_repo.list_by_project(project_id):
                    if char.name in char_names:
                        char_profiles[char.char_id] = {
                            "name": char.name,
                            "core_personality": char.core_personality,
                            "speech_style": char.speech_style or "",
                            "asset_json": char.asset_json or {},
                        }

            # 执行校验
            report = self._llm_check(script, char_profiles, scene_id)

            # 保存报告
            self._save_report(project_id, scene_id, report)

            verdict = report.get("verdict", "UNKNOWN")
            blocking = len(report.get("blocking_issues", []))
            warnings = len(report.get("warning_issues", []))
            log.info(f"校验结果: {verdict} (阻塞:{blocking}, 警告:{warnings})")

        return report

    def _llm_check(self, script: dict, char_profiles: dict, scene_id: str) -> dict:
        """LLM 校验"""
        body_text = json.dumps(script.get("body", []), ensure_ascii=False, indent=2)

        prompt = f"""校验以下剧本的人设一致性。

## 人物设定
{json.dumps(char_profiles, ensure_ascii=False, indent=2)[:2000]}

## 剧本内容
{body_text[:2000]}

按五维校验标准（行为逻辑/语言风格/称谓习惯/人物关系/状态时间线）输出分级校验报告JSON。
"""

        import re as _re
        response = self.call_llm(user_input=prompt)
        json_match = _re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise RuntimeError("LLM 人设校验返回格式异常，未找到有效 JSON")

    def _save_report(self, project_id: str, scene_id: str, report: dict):
        """保存校验报告"""
        output_dir = Path("workspace/projects") / project_id / "work" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}_check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

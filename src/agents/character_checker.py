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
        """LLM 人设一致性校验"""
        body_text = json.dumps(script.get("body", []), ensure_ascii=False, indent=2)

        # 构建人物设定文本（含弧光、关系、内心冲突）
        char_detail = ""
        for cid, cp in char_profiles.items():
            aj = cp.get("asset_json", {})
            char_detail += (
                f"  [{cp['name']}] 性格:{cp.get('core_personality','')} | 语言风格:{cp.get('speech_style','')}\n"
                f"    弧光:{aj.get('character_arc','')} | 内心冲突:{aj.get('inner_conflict','')}\n"
                f"    核心诉求:{aj.get('core_goal','')} | 关系:{json.dumps(aj.get('relationships',{}), ensure_ascii=False)}\n"
                f"    标志行为:{aj.get('signature_behaviors','')} | 关键经历:{'; '.join(aj.get('key_experiences',[])[:3])}\n\n"
            )
        char_detail = char_detail[:2500]

        prompt = f"""严格校验以下场次剧本的人物一致性。每项违规必须标记为 blocking（阻塞）或 warning（警告）。

## 人物资产库（唯一标准）
{char_detail}

## 待校验剧本
场景ID: {scene_id}
{body_text[:2500]}

## 六维校验标准（逐项检查，不可跳过）
1. **行为逻辑**：角色的每个行动是否符合其性格设定和核心诉求？行为是否与弧光阶段一致？
2. **语言风格**：台词是否符合该角色的语言风格和标志性口头禅？称谓习惯是否与人物关系和时代背景一致？
3. **人物关系**：角色互动是否符合已设定的人物关系？关系进展是否过快或出现矛盾？
4. **弧光推进**：本场人物的状态变化是否在其弧光轨迹上？是否出现跳跃或倒退（非设计内的情况才算违规）？
5. **内心冲突**：角色的决策和行为是否反映了其内心冲突？是否出现与内心冲突完全矛盾的行为？
6. **跨场状态连续**：如果前场结尾该角色处于状态A，本场开头不能直接跳到状态C（除非剧情明确展示了中间变化）

输出JSON格式（仅JSON）：
{{
  "scene_id": "{scene_id}",
  "verdict": "PASS | NEEDS_REVISION | NEEDS_REWRITE",
  "blocking_issues": [
    {{"dimension": "六维名称", "character": "角色名", "detail": "具体违规描述和剧本原文引用", "expected": "应该怎样"}}
  ],
  "warning_issues": [
    {{"dimension": "六维名称", "character": "角色名", "detail": "轻微偏差描述", "suggestion": "建议修改方案"}}
  ],
  "arc_progress_check": {{"角色名": {{"current_arc_stage": "当前所处弧光阶段", "is_on_track": true, "note": "说明"}}}},
  "character_voice_score": {{"角色名": "A/B/C/D (台词一致性评分)"}},
  "overall_score": 5
}}"""

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    def _save_report(self, project_id: str, scene_id: str, report: dict):
        """保存校验报告"""
        output_dir = Path("workspace/projects") / project_id / "work" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}_check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

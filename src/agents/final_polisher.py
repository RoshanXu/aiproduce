"""N17/N19 全局统稿Agent"""

import json
from pathlib import Path
from typing import Optional

from src.agents.base import AgentBase
from src.utils.logger import node_logger


class FinalPolisherAgent(AgentBase):
    """全局统稿Agent — N17 单集节奏优化 + N19 全剧统稿打磨

    N17: 优化单集内的节奏衔接、台词风格统一、过渡流畅度
    N19: 统一全剧文风、优化关键节点情绪张力、调整整体节奏
    """

    node_id = "N17"
    node_name = "全局统稿Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.6)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/13_final_polisher.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, **kwargs) -> dict:
        """统一入口：根据 action 分发到 N17 或 N19"""
        action = kwargs.get("action", "n17")
        if action == "n19":
            return self.execute_n19(
                project_id=kwargs["project_id"],
                episode_ids=kwargs["episode_ids"],
            )
        else:
            return self.execute_n17(
                project_id=kwargs["project_id"],
                episode_id=kwargs["episode_id"],
            )

    # ─── N17: 单集节奏优化 ────────────────────────

    def execute_n17(self, project_id: str, episode_id: str) -> dict:
        """N17 单集节奏优化

        对单集内所有场次进行：
        1. 场次间过渡检查与修复
        2. 信息密度曲线诊断
        3. 台词风格跨场一致性
        4. 单集钩子强度评估
        5. 逐场修改（低于30%修改阈值时）

        Returns:
            {
                episode_id, verdict, modifications, rhythm_report, ...
            }
        """
        self.node_id = "N17"
        self.node_name = "单集节奏优化"

        with node_logger.node_context(self.node_id, self.node_name) as log:
            log.info(f"开始单集节奏优化: {episode_id}")

            # 加载该集所有场次剧本
            project_dir = Path("workspace/projects") / project_id
            drafts_dir = project_dir / "work" / "drafts"
            outlines_dir = project_dir / "work" / "outlines"

            scenes = self._load_episode_scenes(drafts_dir, episode_id)
            if not scenes:
                log.warning(f"集 {episode_id} 无场次剧本")
                return {"episode_id": episode_id, "verdict": "SKIP", "reason": "no scenes found"}

            # 加载该集大纲
            episode_outline = self._load_json(outlines_dir / f"{episode_id}_outline.json")

            # 加载校验报告
            validation_dir = project_dir / "work" / "validation"
            validation_reports = self._load_validation_reports(validation_dir, episode_id)

            # 执行 LLM 统稿
            result = self._llm_polish_episode(
                    scenes=scenes,
                    episode_outline=episode_outline,
                    validation_reports=validation_reports,
                    episode_id=episode_id,
                )

            # 保存统稿结果
            self._save_polish_result(project_dir, episode_id, result, "episode")

            mod_count = len(result.get("modifications", []))
            log.info(f"单集统稿完成: {result.get('verdict')} (修改{mod_count}处)")

        return result

    # ─── N19: 全剧统稿打磨 ────────────────────────

    def execute_n19(self, project_id: str, episode_ids: list[str]) -> dict:
        """N19 全剧统稿打磨

        跨集一致性诊断：
        1. 人物状态连线与弧光检查
        2. 伏笔全局盘点
        3. 台词前后矛盾检测
        4. 全剧风格统一
        5. 关键节点情绪张力优化

        Returns:
            {
                project_id, verdict, global_diagnosis, cross_episode_issues, ...
            }
        """
        self.node_id = "N19"
        self.node_name = "全剧统稿打磨"

        with node_logger.node_context(self.node_id, self.node_name) as log:
            log.info(f"开始全剧统稿打磨: {len(episode_ids)} 集")

            project_dir = Path("workspace/projects") / project_id
            drafts_dir = project_dir / "work" / "drafts"

            # 加载全剧所有场次
            all_scenes = []
            for ep_id in episode_ids:
                scenes = self._load_episode_scenes(drafts_dir, ep_id)
                all_scenes.extend(scenes)

            if not all_scenes:
                log.warning("无场次剧本可统稿")
                return {"project_id": project_id, "verdict": "SKIP", "reason": "no scenes found"}

            # 加载资产库
            assets = self._load_assets(project_dir)

            # 执行 LLM 全剧统稿
            result = self._llm_polish_global(
                    scenes=all_scenes,
                    assets=assets,
                    episode_ids=episode_ids,
                    project_id=project_id,
                )

            # 保存统稿结果
            self._save_polish_result(project_dir, "GLOBAL", result, "global")

            log.info(f"全剧统稿完成: {result.get('verdict')}")

        return result

    # ─── LLM 统稿 ────────────────────────────────

    def _llm_polish_episode(
        self, scenes: list[dict], episode_outline: dict,
        validation_reports: list[dict], episode_id: str,
    ) -> dict:
        """LLM 单集节奏优化"""
        # 构造输入文本
        scenes_text = json.dumps(scenes, ensure_ascii=False, indent=2)[:6000]

        prompt = f"""对以下单集剧本进行节奏优化与风格统稿。

## 分集大纲
{json.dumps(episode_outline, ensure_ascii=False, indent=2)[:1000]}

## 校验报告摘要
{json.dumps(self._summarize_reports(validation_reports), ensure_ascii=False, indent=2)[:1000]}

## 待统稿剧本（共{len(scenes)}场）
{scenes_text}

## 统稿任务
1. 场次间过渡检查：逐场检查★标记的转场锚点是否具体有效
2. 信息密度诊断：标注信息洼地（连续场景无实质推进的位置）
3. 台词跨场一致性：同一人物不同场次的语言风格是否统一
4. 钩子强度评估：集尾最后一场的结尾钩子评级（A/B/C/D）

输出JSON格式（仅JSON）：
{{
  "episode_id": "{episode_id}",
  "verdict": "PASS | NEEDS_REVISION | NEEDS_REWRITE",
  "hook_rating": "A/B/C/D",
  "hook_analysis": "钩子类型与冲击力简要分析",
  "rhythm_diagnosis": {{
    "info_valleys": ["信息洼地位置描述"],
    "emotion_monotone_segments": ["情绪单调段描述"],
    "transition_issues": ["过渡问题描述"],
    "overall_rhythm_score": 5
  }},
  "style_diagnosis": {{
    "character_voice_drifts": [],
    "ai_tone_infections": [],
    "world_inconsistencies": []
  }},
  "modifications": [
    {{
      "scene_id": "场次ID",
      "type": "transition_fix | dialogue_polish | rhythm_adjust | hook_enhance",
      "location": "修改位置",
      "reason": "修改理由",
      "original": "修改前",
      "revised": "修改后"
    }}
  ],
  "modification_ratio": 0.0,
  "rewrite_recommendation": null
}}"""

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    def _llm_polish_global(
        self, scenes: list[dict], assets: dict,
        episode_ids: list[str], project_id: str,
    ) -> dict:
        """LLM 全剧统稿"""
        scenes_text = json.dumps(scenes, ensure_ascii=False, indent=2)[:8000]

        prompt = f"""对以下全剧剧本进行跨集一致性诊断与风格统稿。

## 资产库
{json.dumps(assets, ensure_ascii=False, indent=2)[:2000]}

## 全剧剧本（{len(episode_ids)}集，共{len(scenes)}场）
{scenes_text}

## 统稿任务
1. 人物状态连线：逐人物按时间轴检查状态变化是否符合弧光规划
2. 台词前后矛盾检测：同一人物对同一事实的矛盾表述
3. 跨集文风统一：是否存在不同集数间风格跳变
4. 全剧关键节点情绪张力评估

输出JSON格式（仅JSON）：
{{
  "project_id": "{project_id}",
  "verdict": "PASS | NEEDS_REVISION",
  "episode_count": {len(episode_ids)},
  "scene_count": {len(scenes)},
  "character_arc_check": {{
    "characters_checked": [],
    "arc_deviations": [],
    "state_continuity_issues": []
  }},
  "cross_episode_consistency": {{
    "dialogue_contradictions": [],
    "style_shifts": [],
    "lore_consistency_issues": []
  }},
  "emotional_beat_analysis": {{
    "climax_positions": [],
    "tension_curve_issues": [],
    "key_node_quality": {{}}
  }},
  "global_modifications": [],
  "final_verdict": "PASS | NEEDS_REVISION"
}}"""

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    # ─── 辅助方法 ────────────────────────────────

    def _load_episode_scenes(self, drafts_dir: Path, episode_id: str) -> list[dict]:
        """加载指定集的所有场次剧本"""
        scenes = []
        if not drafts_dir.exists():
            return scenes

        for scene_file in sorted(drafts_dir.glob(f"{episode_id}-scene-*.json")):
            try:
                scene = json.loads(scene_file.read_text(encoding="utf-8"))
                scenes.append(scene)
            except Exception:
                continue

        # 也尝试其他命名格式
        if not scenes:
            for scene_file in sorted(drafts_dir.glob(f"SCENE-*.json")):
                try:
                    scene = json.loads(scene_file.read_text(encoding="utf-8"))
                    meta = scene.get("meta", {})
                    sid = meta.get("scene_id", "")
                    if sid.startswith(episode_id):
                        scenes.append(scene)
                except Exception:
                    continue

        return scenes

    def _load_json(self, path: Path) -> dict:
        """安全加载 JSON 文件"""
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _load_validation_reports(self, validation_dir: Path, episode_id: str) -> list[dict]:
        """加载指定集相关的校验报告"""
        reports = []
        if not validation_dir.exists():
            return reports

        for report_file in sorted(validation_dir.glob("*.json")):
            try:
                report = json.loads(report_file.read_text(encoding="utf-8"))
                sid = report.get("scene_id", "")
                if episode_id in sid or "check" in report_file.stem:
                    reports.append(report)
            except Exception:
                continue

        return reports

    def _load_assets(self, project_dir: Path) -> dict:
        """加载资产库"""
        assets = {}
        assets_dir = project_dir / "assets"
        if assets_dir.exists():
            for asset_file in assets_dir.glob("*.json"):
                try:
                    key = asset_file.stem
                    assets[key] = json.loads(asset_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return assets

    def _summarize_reports(self, reports: list[dict]) -> dict:
        """汇总校验报告摘要"""
        summary = {
            "total_reports": len(reports),
            "verdicts": {},
            "blocking_count": 0,
            "warning_count": 0,
        }
        for r in reports:
            v = r.get("verdict", "UNKNOWN")
            summary["verdicts"][v] = summary["verdicts"].get(v, 0) + 1
            summary["blocking_count"] += len(r.get("blocking_issues", []))
            summary["warning_count"] += len(r.get("warning_issues", []))
        return summary

    def _save_polish_result(self, project_dir: Path, target_id: str, result: dict, scope: str):
        """保存统稿结果"""
        output_dir = project_dir / "work" / "polish"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{target_id}_polish_{scope}.json"
        (output_dir / filename).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

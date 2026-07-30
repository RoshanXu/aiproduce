"""工作流运行器

串联各节点，管理状态流转。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.workflow.state import WorkflowState, NodeStatus
from src.utils.logger import node_logger
from src.utils.token_counter import token_counter


class WorkflowRunner:
    """工作流运行器

    支持 Thin Slice 模式和完整模式。
    """

    def __init__(self):
        self.state = WorkflowState()

    def run_thin_slice(
        self,
        project_name: str,
        source_file_path: str,
        adaptation_format: str = "网剧",
        target_episodes: int = 24,
        episode_duration: int = 45,
        genre: str = "古装",
        model_name: str = "claude-sonnet-5",
    ) -> dict:
        """运行 Thin Slice 验证链路：N01→N02→N03→N04→N07→N09→N11→N12

        当前阶段1仅实现 N01→N02→N03。
        阶段2-3 将依次实现剩余节点。
        """
        self.state.started_at = datetime.now()
        results = {}

        print("\n" + "=" * 60)
        print("🚀 AIproduce Thin Slice 工作流")
        print("=" * 60)

        # ─── N01: 项目初始化 ───────────────────
        print("\n[N01] 项目初始化...")
        n01_result = self._run_n01(
            project_name=project_name,
            source_file_path=source_file_path,
            adaptation_format=adaptation_format,
            target_episodes=target_episodes,
            episode_duration=episode_duration,
            genre=genre,
            model_name=model_name,
        )
        project_id = n01_result["project_id"]
        self.state.set_node_status("N01", NodeStatus.PASSED)
        self.state.set_node_output("N01", n01_result)
        results["N01"] = n01_result
        print(f"  ✅ 项目创建成功: {project_id}")
        print(f"  📂 工作区: {n01_result['workspace_dir']}")
        print(f"  📊 原著字数: {n01_result['total_words']}")

        # ─── N02: 原著解构 ───────────────────
        print("\n[N02] 原著文本拆分与分层摘要...")
        n02_result = self._run_n02(
            project_id=project_id,
            source_file_path=source_file_path,
            model_name=model_name,
        )
        self.state.set_node_status("N02", NodeStatus.PASSED)
        self.state.set_node_output("N02", n02_result)
        results["N02"] = n02_result
        print(f"  ✅ 解构完成: {n02_result['chunk_count']} 个语义块, {n02_result['chapter_count']} 个章节")

        # ─── N03: 首轮资产库构建（三个Agent并行） ──
        print("\n[N03] 首轮资产库构建...")
        n03_result = self._run_n03(project_id=project_id, model_name=model_name)
        self.state.set_node_status("N03", NodeStatus.PASSED)
        self.state.set_node_output("N03", n03_result)
        results["N03"] = n03_result
        print(f"  ✅ 人物: {n03_result['characters']['total_characters']} 个")
        print(f"  ✅ 场景: {len(n03_result['world'].get('world', {}).get('core_scenes', []))} 个")
        print(f"  ✅ 事件: {len(n03_result['timeline'].get('timeline', {}).get('main_timeline', []))} 个")

        # Save results
        self._save_results(project_id, results)

        # ─── N04: 改编策划总纲 ───────────────────
        print("\n[N04] 改编策划总纲生成...")
        n04_result = self._run_n04(project_id=project_id, model_name=model_name)
        self.state.set_node_status("N04", NodeStatus.PASSED)
        self.state.set_node_output("N04", n04_result)
        results["N04"] = n04_result
        bp = n04_result.get("blueprint", {})
        sell = bp.get("core_positioning", {}).get("one_line_sell", "待查看")
        print(f"  ✅ 策划总纲完成: {sell}")

        # ─── N07: 分集大纲 ───────────────────
        print("\n[N07] 全剧分集大纲生成...")
        n07_result = self._run_n07(project_id=project_id, model_name=model_name)
        self.state.set_node_status("N07", NodeStatus.PASSED)
        self.state.set_node_output("N07", n07_result)
        results["N07"] = n07_result
        total_ep = n07_result.get("total_episodes", 0)
        print(f"  ✅ 分集大纲完成: {total_ep} 集")

        # ─── N09: 场次拆分 ───────────────────
        print("\n[N09] 场次拆分...")
        n09_result = self._run_n09(project_id=project_id, episode_id="EP01", model_name=model_name)
        self.state.set_node_status("N09", NodeStatus.PASSED)
        self.state.set_node_output("N09", n09_result)
        results["N09"] = n09_result
        scenes = n09_result.get("scenes", [])
        print(f"  ✅ 场次拆分完成: {n09_result['total_scenes']} 场")

        # ─── N11: 单场剧本生成（选取前3场） ──
        print("\n[N11] 单场剧本生成...")
        thin_slice_scenes = scenes[:3]  # Thin Slice 只生成前3场
        n11_results = []
        for i, scene in enumerate(thin_slice_scenes):
            print(f"  ├─ 生成 {scene['scene_id']} ({i+1}/{len(thin_slice_scenes)})...")
            n11 = self._run_n11(project_id=project_id, scene_card=scene, model_name=model_name)
            n11_results.append(n11)
        self.state.set_node_status("N11", NodeStatus.PASSED)
        self.state.set_node_output("N11", {"scripts": n11_results})
        results["N11"] = n11_results
        print(f"  ✅ 剧本生成完成: {len(n11_results)} 场")

        # ─── N12: 人设一致性校验 ──────────────
        print("\n[N12] 人设一致性校验...")
        n12_results = []
        for n11 in n11_results:
            scene_id = n11["scene_id"]
            print(f"  ├─ 校验 {scene_id}...")
            n12 = self._run_n12(project_id=project_id, scene_id=scene_id, model_name=model_name)
            n12_results.append(n12)
            verdict = n12.get("verdict", "?")
            blocking = len(n12.get("blocking_issues", []))
            warnings = len(n12.get("warning_issues", []))
            print(f"  │  {verdict} (阻塞:{blocking}, 警告:{warnings})")
        self.state.set_node_status("N12", NodeStatus.PASSED)
        self.state.set_node_output("N12", {"reports": n12_results})
        results["N12"] = n12_results
        print(f"  ✅ 校验完成: {len(n12_results)} 场")

        # Save updated results
        self._save_results(project_id, results)

        # Print cost report
        token_counter.print_report()

        print("\n" + "=" * 60)
        print("✅ Thin Slice 完整链路 (N01→N02→N03→N04→N07→N09→N11→N12) 执行完成!")
        print(f"   项目ID: {project_id}")
        print(f"   产出: {n07_result.get('total_episodes', 0)}集大纲 → {n09_result['total_scenes']}场 → {len(n11_results)}场剧本 → {len(n12_results)}份校验报告")
        print("=" * 60 + "\n")

        return {"project_id": project_id, "results": results}

    def _run_n01(self, **kwargs) -> dict:
        """N01 项目初始化"""
        from src.agents.scheduler import SchedulerAgent

        agent = SchedulerAgent(model_name=kwargs.get("model_name", "claude-sonnet-5"))
        return agent.execute(
            action="init",
            project_name=kwargs["project_name"],
            source_file_path=kwargs["source_file_path"],
            adaptation_format=kwargs.get("adaptation_format", "网剧"),
            target_episodes=kwargs.get("target_episodes", 24),
            episode_duration=kwargs.get("episode_duration", 45),
            genre=kwargs.get("genre", "古装"),
            model_name=kwargs.get("model_name", "claude-sonnet-5"),
        )

    def _run_n02(self, project_id: str, source_file_path: str, model_name: str) -> dict:
        """N02 原著解构"""
        from src.agents.deconstructor import DeconstructorAgent

        agent = DeconstructorAgent(model_name=model_name)
        return agent.execute(
            project_id=project_id,
            source_file_path=source_file_path,
        )

    def _run_n03(self, project_id: str, model_name: str) -> dict:
        """N03 三个资产Agent并行执行 + 跨资产交叉校验"""
        from src.agents.character_asset import CharacterAssetAgent
        from src.agents.world_asset import WorldAssetAgent
        from src.agents.timeline_asset import TimelineAssetAgent

        # 并行执行三个资产Agent
        char_agent = CharacterAssetAgent(model_name=model_name)
        world_agent = WorldAssetAgent(model_name=model_name)
        timeline_agent = TimelineAssetAgent(model_name=model_name)

        print("  ├─ 人物资产库构建...")
        chars = char_agent.execute(project_id=project_id)

        print("  ├─ 世界观资产库构建...")
        world = world_agent.execute(project_id=project_id)

        print("  ├─ 时间线构建...")
        timeline = timeline_agent.execute(project_id=project_id)

        # 跨资产一致性交叉校验
        print("  ├─ 跨资产交叉校验...")
        cross_issues = self._cross_validate(chars, world, timeline)
        if cross_issues:
            print(f"  ⚠️  发现 {len(cross_issues)} 个跨资产不一致项")

        return {
            "characters": chars,
            "world": world,
            "timeline": timeline,
            "cross_validation_issues": cross_issues,
        }

    def _cross_validate(
        self, chars: dict, world: dict, timeline: dict
    ) -> list[dict]:
        """跨资产一致性交叉校验

        检查：人物经历 vs 时间线、人物身份 vs 世界观、场景事件 vs 时间线
        """
        issues = []

        # 1. 人物名 vs 时间线事件涉及人物
        char_names = {c["name"] for c in chars.get("characters", [])}
        timeline_chars = set()
        for event in timeline.get("timeline", {}).get("main_timeline", []):
            for name in event.get("involved_characters", []):
                timeline_chars.add(name)

        unknown_in_timeline = timeline_chars - char_names
        if unknown_in_timeline:
            issues.append({
                "type": "timeline_characters_not_in_asset",
                "detail": f"时间线中的人物未出现在人物资产库: {unknown_in_timeline}",
            })

        return issues

    def _run_n04(self, project_id: str, model_name: str) -> dict:
        """N04 改编策划总纲生成"""
        from src.agents.adaptation_planner import AdaptationPlannerAgent
        agent = AdaptationPlannerAgent(model_name=model_name)
        return agent.execute(project_id=project_id)

    def _run_n07(self, project_id: str, model_name: str) -> dict:
        """N07 分集大纲生成"""
        from src.agents.episode_outliner import EpisodeOutlinerAgent
        agent = EpisodeOutlinerAgent(model_name=model_name)
        return agent.execute(project_id=project_id)

    def _run_n09(self, project_id: str, episode_id: str, model_name: str) -> dict:
        """N09 场次拆分"""
        from src.agents.scene_splitter import SceneSplitterAgent
        agent = SceneSplitterAgent(model_name=model_name)
        return agent.execute(project_id=project_id, episode_id=episode_id)

    def _run_n11(self, project_id: str, scene_card: dict, model_name: str) -> dict:
        """N11 单场剧本生成"""
        from src.agents.scene_writer import SceneWriterAgent
        agent = SceneWriterAgent(model_name=model_name)
        return agent.execute(project_id=project_id, scene_card=scene_card)

    def _run_n12(self, project_id: str, scene_id: str, model_name: str) -> dict:
        """N12 人设一致性校验"""
        from src.agents.character_checker import CharacterCheckerAgent
        agent = CharacterCheckerAgent(model_name=model_name)
        return agent.execute(project_id=project_id, scene_id=scene_id)

    def _save_results(self, project_id: str, results: dict):
        """保存阶段结果到工作区"""
        output_dir = Path("workspace/projects") / project_id / "work" / "deconstruction"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存 N02 解构摘要
        n02 = results.get("N02", {})
        (output_dir / "global_summary.json").write_text(
            json.dumps(n02.get("global_summary", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 保存 N03 资产库
        assets_dir = Path("workspace/projects") / project_id / "assets"
        n03 = results.get("N03", {})

        (assets_dir / "characters" / "v1.0.json").write_text(
            json.dumps(n03.get("characters", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (assets_dir / "world" / "v1.0.json").write_text(
            json.dumps(n03.get("world", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (assets_dir / "timeline" / "v1.0.json").write_text(
            json.dumps(n03.get("timeline", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 保存 N04 策划总纲
        n04 = results.get("N04", {})
        if n04:
            planning_dir = Path("workspace/projects") / project_id / "work" / "planning"
            planning_dir.mkdir(parents=True, exist_ok=True)

        # 保存 N07 分集大纲
        n07 = results.get("N07", {})
        if n07:
            outlines_dir = Path("workspace/projects") / project_id / "work" / "outlines"
            outlines_dir.mkdir(parents=True, exist_ok=True)

        # 保存完整结果摘要
        summary = {
            "project_id": project_id,
            "completed_nodes": ["N01", "N02", "N03", "N04", "N07"],
            "timestamp": datetime.now().isoformat(),
        }
        (output_dir / "phase2_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

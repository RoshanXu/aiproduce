"""N07 分集大纲Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import (
    ProjectRepository, SummaryRepository,
    CharacterRepository, WorldRepository, TimelineRepository,
)
from src.utils.logger import node_logger


class EpisodeOutlinerAgent(AgentBase):
    """分集大纲Agent — N07 全剧分集大纲生成

    基于改编策划总纲和资产库，生成完整的分集大纲。
    """

    node_id = "N07"
    node_name = "分集大纲Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.7, max_tokens=16384)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/07_episode_outliner.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str) -> dict:
        """生成分集大纲

        Returns:
            {outline: dict, total_episodes: int}
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 加载上下文
            log.info("加载上游数据...")
            context = self._load_context(project_id)

            # 生成大纲
            outline = self._llm_generate(context)

            # 保存
            self._save_outline(project_id, outline)

            log.info(f"分集大纲生成完成: {outline.get('total_episodes', 0)} 集")

        return {"outline": outline, "total_episodes": outline.get("total_episodes", 0)}

    def _load_context(self, project_id: str) -> dict:
        """加载完整上下文，包括人物资产、世界观、时间线"""
        context = {}

        with get_session() as session:
            # 策划总纲
            blueprint_path = Path("workspace/projects") / project_id / "work" / "planning" / "adaptation_blueprint.json"
            if blueprint_path.exists():
                context["blueprint"] = json.loads(blueprint_path.read_text(encoding="utf-8"))

            # 全局摘要
            summary_repo = SummaryRepository(session)
            global_sum = summary_repo.get_by_type(project_id, "global")
            if global_sum:
                context["global_summary"] = global_sum.summary_json.get("summary", "")

            # ── 人物资产（完整档案） ──
            char_repo = CharacterRepository(session)
            chars = char_repo.list_by_project(project_id)
            context["character_count"] = len(chars)
            context["main_characters"] = [c.name for c in chars[:5]]
            # 构建人物档案摘要（注入 prompt 用）
            char_profiles = []
            for c in chars[:10]:
                aj = c.asset_json or {}
                profile = {
                    "name": c.name,
                    "core_identity": c.core_identity or "",
                    "core_personality": c.core_personality or "",
                    "speech_style": c.speech_style or "",
                    "core_goal": aj.get("core_goal", ""),
                    "character_arc": aj.get("character_arc", ""),
                    "relationships": aj.get("relationships", {}),
                    "key_experiences": aj.get("key_experiences", []),
                    "inner_conflict": aj.get("inner_conflict", ""),
                }
                char_profiles.append(profile)
            context["character_profiles"] = char_profiles

            # ── 世界观资产 ──
            world_repo = WorldRepository(session)
            world_records = world_repo.list_by_project(project_id)
            world_context = {}
            for wr in world_records[:1]:  # 取主世界观
                aj = wr.asset_json or {}
                basic = aj.get("basic_settings", {})
                culture = aj.get("culture_details", {})
                scenes = aj.get("core_scenes", [])
                world_context = {
                    "era_background": basic.get("era_background", wr.era_background or ""),
                    "geography": basic.get("geography", wr.geography or ""),
                    "core_factions": basic.get("core_factions", []),
                    "social_hierarchy": basic.get("social_hierarchy", ""),
                    "universal_rules": basic.get("universal_rules", ""),
                    "core_locations": [s.get("scene_name", "") for s in scenes[:8]],
                    "costume_rules": culture.get("costume_rules", ""),
                    "etiquette": culture.get("etiquette_and_titles", ""),
                }
            context["world"] = world_context

            # ── 时间线资产 ──
            timeline_repo = TimelineRepository(session)
            tl_records = timeline_repo.list_by_project(project_id)
            timeline_context = {}
            for tl in tl_records[:1]:
                aj = tl.asset_json or {}
                main_tl = aj.get("main_timeline", [])
                foreshadows = aj.get("foreshadow_table", [])
                timeline_context = {
                    "key_events": [
                        {"time": e.get("time_point", ""), "event": e.get("event_description", "")}
                        for e in main_tl[:15]
                    ],
                    "pending_foreshadows": [
                        {"id": f.get("foreshadow_id", ""), "plant": f.get("plant_content", ""),
                         "chapter": f.get("plant_chapter", ""), "status": f.get("status", "pending")}
                        for f in foreshadows if f.get("status") == "pending"
                    ],
                }
            context["timeline"] = timeline_context

            # 项目配置
            proj_repo = ProjectRepository(session)
            project = proj_repo.get(project_id)
            if project:
                config = project.config_json or {}
                context["episodes"] = config.get("target_episodes", 24)
                context["duration"] = config.get("episode_duration_min", 45)

        return context

    def _llm_generate(self, context: dict) -> dict:
        """LLM 逐集生成分集大纲

        每次只生成 1 集，注入完整资产库确保跨集一致性。
        """
        total_ep = context.get("episodes", 24)
        duration = context.get("duration", 45)

        # ── 公共上下文（每集共享，只构建一次） ──
        # 人物档案
        char_text = ""
        for c in context.get("character_profiles", []):
            rels = ", ".join(f"{k}→{v}" for k, v in c.get("relationships", {}).items())
            char_text += (
                f"  - {c['name']} | {c.get('core_identity','')} | 性格:{c.get('core_personality','')}\n"
                f"    语言风格:{c.get('speech_style','')} | 核心诉求:{c.get('core_goal','')}\n"
                f"    弧光:{c.get('character_arc','')} | 内心冲突:{c.get('inner_conflict','')}\n"
                f"    关系:{rels or '暂无'} | 关键经历:{'; '.join(c.get('key_experiences',[])[:3])}\n"
            )

        # 世界观
        w = context.get("world", {})
        world_text = (
            f"  时代背景: {w.get('era_background','')}\n"
            f"  地理: {w.get('geography','')}\n"
            f"  势力: {', '.join(w.get('core_factions',[]))}\n"
            f"  核心场景: {', '.join(w.get('core_locations',[]))}\n"
            f"  通用规则: {w.get('universal_rules','')}\n"
            f"  礼仪称谓: {w.get('etiquette','')}\n"
        )

        # 时间线/伏笔
        t = context.get("timeline", {})
        foreshadow_text = ""
        for f in t.get("pending_foreshadows", []):
            foreshadow_text += f"  - [{f.get('id','')}] {f.get('plant','')} (原著第{f.get('chapter','?')}章)\n"
        events_text = ""
        for e in t.get("key_events", [])[:10]:
            events_text += f"  - {e.get('time','')}: {e.get('event','')}\n"

        shared_context = f"""## 改编策划总纲
{json.dumps(context.get('blueprint', {}), ensure_ascii=False, indent=2)[:2000]}

## 全局摘要
{context.get('global_summary', '')[:800]}

## 人物资产库（必须严格遵循）
{char_text}

## 世界观设定（所有情节必须符合）
{world_text}

## 原著关键事件时间线
{events_text}

## 待回收伏笔（请在合适集数安排回收）
{foreshadow_text or '（暂无待回收伏笔）'}"""

        with node_logger.node_context(self.node_id, self.node_name) as log:
            all_episodes = []
            prev_episode_json = ""  # 前一集完整数据，用于衔接

            for ep_num in range(1, total_ep + 1):
                log.info(f"  生成 EP{ep_num:02d}/{total_ep:02d} ({duration}分钟)...")

                ep_prompt = f"""{shared_context}

## 前集完整大纲（必须无缝衔接）
{prev_episode_json or '（本集为第 1 集，无前情）'}

## 本集任务
生成第 {ep_num} 集（共 {total_ep} 集，{duration} 分钟/集）的分集大纲。

**硬性约束（违反则不合格）：**
1. 结尾钩子必须与前集结尾钩子形成因果链，不能凭空出现
2. 人物状态必须与前集结束时的状态连续（禁止跳跃式变化）
3. 如有待回收伏笔与本集相关，必须在 key_beats 中安排埋设或回收
4. 核心冲突须具体——"主角遇到困难"不合格，"主角发现糖水铺面临拆迁通知，必须在3天内筹到30万"合格
5. 人物成长节点需引用人物弧光表中的阶段

请输出 JSON（仅 JSON）：
{{
  "episode_id": "EP{ep_num:02d}",
  "episode_number": {ep_num},
  "duration_min": {duration},
  "summary": "本集概述（200-500字）",
  "core_conflict": "核心冲突（必须具体）",
  "ending_hook": "结尾钩子（必须与前集钩子形成因果链）",
  "character_development": "人物成长节点（引用弧光阶段）",
  "character_states_end": {{"人物名": "本集结束时的状态"}},
  "foreshadow_planted": ["本集埋设的伏笔"],
  "foreshadow_resolved": ["本集回收的伏笔"],
  "key_beats": ["本集关键节拍1", "本集关键节拍2", "本集关键节拍3"]
}}"""
                response = self.call_llm(user_input=ep_prompt)
                ep_data = self._parse_json_response(response)

                # 确保必要字段存在
                ep_data.setdefault("episode_id", f"EP{ep_num:02d}")
                ep_data.setdefault("episode_number", ep_num)
                all_episodes.append(ep_data)

                # 前一集完整数据作为下一集的衔接上下文
                prev_episode_json = json.dumps({
                    "episode_number": ep_num,
                    "summary": ep_data.get("summary", ""),
                    "core_conflict": ep_data.get("core_conflict", ""),
                    "ending_hook": ep_data.get("ending_hook", ""),
                    "character_states_end": ep_data.get("character_states_end", {}),
                    "foreshadow_planted": ep_data.get("foreshadow_planted", []),
                }, ensure_ascii=False)

        return {
            "total_episodes": total_ep,
            "episodes": all_episodes,
            "adaptation_overview": context.get("blueprint", {}).get("改编核心定位", ""),
        }

    def _save_outline(self, project_id: str, outline: dict):
        """保存分集大纲"""
        output_dir = Path("workspace/projects") / project_id / "work" / "outlines"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "series_outline.json").write_text(
            json.dumps(outline, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 同时保存到每个单集文件
        for ep in outline.get("episodes", []):
            ep_file = output_dir / f"{ep['episode_id']}.json"
            ep_file.write_text(
                json.dumps(ep, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

"""N04 改编策划Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import (
    ProjectRepository, ChunkRepository, SummaryRepository,
    CharacterRepository, WorldRepository,
)
from src.utils.logger import node_logger


class AdaptationPlannerAgent(AgentBase):
    """改编策划Agent — N04 改编策划总纲生成

    基于全局摘要和资产库，输出《改编策划总纲》。
    """

    node_id = "N04"
    node_name = "改编策划Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.7, max_tokens=16384)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/06_adaptation_planner.md")
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8")
            # 去掉文件头部的 frontmatter
            if "# 改编策划Agent Prompt" in content:
                self.prompt_template = content
            else:
                self.prompt_template = content

    def execute(self, project_id: str) -> dict:
        """生成改编策划总纲

        Returns:
            {blueprint: dict} 改编策划总纲
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 1. 加载上游数据
            log.info("加载上游数据...")
            context = self._load_context(project_id)

            # 2. 尝试 LLM 生成
            blueprint = self._llm_generate(context)

            # 3. 保存到工作区
            self._save_blueprint(project_id, blueprint)

            log.info(f"改编策划总纲生成完成")

        return {"blueprint": blueprint}

    def _load_context(self, project_id: str) -> dict:
        """加载上下文数据"""
        context = {}

        # 全局摘要
        with get_session() as session:
            summary_repo = SummaryRepository(session)
            global_sum = summary_repo.get_by_type(project_id, "global")
            if global_sum:
                context["global_summary"] = global_sum.summary_json.get("summary", "")

            # 人物列表
            char_repo = CharacterRepository(session)
            chars = char_repo.list_by_project(project_id)
            context["character_list"] = [
                {"name": c.name, "core_identity": c.core_identity, "core_personality": c.core_personality}
                for c in chars[:15]
            ]

            # 世界观
            world_repo = WorldRepository(session)
            world = world_repo.get_by_project(project_id)
            if world:
                w = world.asset_json or {}
                context["world_brief"] = w.get("basic_settings", {}).get("era_background", "")

            # 项目配置
            proj_repo = ProjectRepository(session)
            project = proj_repo.get(project_id)
            if project:
                config = project.config_json or {}
                context["format"] = config.get("adaptation_format", "网剧")
                context["episodes"] = config.get("target_episodes", 24)
                context["duration"] = config.get("episode_duration_min", 45)
                context["audience"] = config.get("target_audience", "18-35岁")
                context["direction"] = config.get("adaptation_direction", "")

        return context

    def _llm_generate(self, context: dict) -> dict:
        """LLM 生成改编策划总纲"""
        prompt = self._build_prompt(context)

        response = self.call_llm(user_input=prompt)
        return self._parse_json_response(response)

    def _build_prompt(self, context: dict) -> str:
        """构建 LLM prompt"""
        return f"""# 改编策划总纲生成

## 原著信息
- 全局摘要：{context.get('global_summary', '待加载')}
- 核心人物：{json.dumps(context.get('character_list', []), ensure_ascii=False)}
- 世界观：{context.get('world_brief', '待补充')}

## 项目配置
- 改编形式：{context.get('format', '网剧')}
- 目标：{context.get('episodes', 24)}集 × {context.get('duration', 45)}分钟
- 受众：{context.get('audience', '18-35岁')}
- 改编方向：{context.get('direction', '保留原作核心')}

## 要求
请输出完整的改编策划总纲，包含以下模块：
1. 改编核心定位（一句话核心卖点、受众定位、叙事风格）
2. 主线与支线取舍方案（保留线、删减线、合并角色、保留名场面）
3. 全局三幕式结构规划
4. 主角人物弧光重构
5. 世界观落地策略
6. 风险提示与适配建议

输出格式：JSON
"""

    def _save_blueprint(self, project_id: str, blueprint: dict):
        """保存策划总纲到工作区"""
        output_dir = Path("workspace/projects") / project_id / "work" / "planning"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "adaptation_blueprint.json").write_text(
            json.dumps(blueprint, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
        super().__init__(model_name=model_name, temperature=0.7)
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
        """加载上下文"""
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

            # 资产库
            char_repo = CharacterRepository(session)
            chars = char_repo.list_by_project(project_id)
            context["character_count"] = len(chars)
            context["main_characters"] = [c.name for c in chars[:5]]

            # 项目配置
            proj_repo = ProjectRepository(session)
            project = proj_repo.get(project_id)
            if project:
                config = project.config_json or {}
                context["episodes"] = config.get("target_episodes", 24)
                context["duration"] = config.get("episode_duration_min", 45)

        return context

    def _llm_generate(self, context: dict) -> dict:
        """LLM 生成分集大纲"""
        total_ep = context.get("episodes", 24)

        prompt = f"""基于以下信息，生成 {total_ep} 集分集大纲。

## 改编策划总纲
{json.dumps(context.get('blueprint', {}), ensure_ascii=False, indent=2)[:2000]}

## 全局摘要
{context.get('global_summary', '')[:1000]}

## 核心人物
{', '.join(context.get('main_characters', []))}

## 要求
- 总集数: {total_ep} 集 × {context.get('duration', 45)} 分钟
- 按三幕式结构分配: 第一幕 {total_ep//4}集, 第二幕 {total_ep//2}集, 第三幕 {total_ep - total_ep//4 - total_ep//2}集
- 每集必须有: 核心冲突、结尾钩子、人物成长节点

请输出完整的JSON格式分集大纲。
"""

        import re as _re
        response = self.call_llm(user_input=prompt)
        json_match = _re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise RuntimeError("LLM 分集大纲返回格式异常，未找到有效 JSON")

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

"""N01/N15/N16/N21 项目调度Agent"""

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from src.agents.base import AgentBase
from src.db.engine import init_db, get_session
from src.db.repository import ProjectRepository
from src.db.models import ProjectRecord
from src.store.chroma_store import ChromaStore
from src.models.project import ProjectConfig, AdaptationFormat, GenreType, ModelTier
from src.utils.text_utils import load_novel, count_chinese_words


class SchedulerAgent(AgentBase):
    """项目调度Agent — 全流程大脑

    负责 N01（项目初始化）、N15（剧本入库）、N16（单集拼接）、N21（项目结项归档）
    """

    node_id = "N01"
    node_name = "项目调度Agent"

    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("DEFAULT_MODEL", "claude-sonnet-5")
        super().__init__(model_name=model_name, temperature=0.3)

    def execute(self, **kwargs) -> dict:
        """N01/N15/N16/N21: 项目调度"""
        action = kwargs.pop("action", "init")
        if action == "init":
            # 注入 self.model_name（从 .env DEFAULT_MODEL 读取）
            if "model_name" not in kwargs:
                kwargs["model_name"] = self.model_name
            return self._init_project(**kwargs)
        elif action == "archive_scene":
            return self._archive_scene(**kwargs)
        elif action == "stitch_episode":
            return self._stitch_episode(**kwargs)
        elif action == "archive_project":
            return self._archive_project(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _init_project(
        self,
        project_name: str,
        source_file_path: str,
        adaptation_format: str = "网剧",
        target_episodes: int = 24,
        episode_duration: int = 45,
        genre: str = "古装",
        target_audience: str = "18-35岁",
        adaptation_direction: str = "",
        model_tier: str = "32K",
        model_name: str = "claude-sonnet-5",
    ) -> dict:
        """N01: 创建新项目的完整初始化流程

        Returns:
            {project_id, workspace_dir, project_config}
        """
        # 生成项目ID
        project_id = f"PROJ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # 加载原著文件
        source_path = Path(source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"原著文件不存在: {source_file_path}")

        novel_text = load_novel(source_path)
        total_words = count_chinese_words(novel_text)

        # 创建工作区目录结构
        base_dir = Path("workspace")
        project_dir = base_dir / "projects" / project_id
        asset_dir = project_dir / "assets"
        work_dir = project_dir / "work"
        scripts_dir = project_dir / "scripts"

        dirs = [
            asset_dir / "characters",
            asset_dir / "world",
            asset_dir / "timeline",
            work_dir / "deconstruction",
            work_dir / "planning",
            work_dir / "outlines",
            work_dir / "scene_cards",
            work_dir / "drafts",
            work_dir / "validation",
            scripts_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # 构建项目配置
        config = ProjectConfig(
            project_id=project_id,
            project_name=project_name,
            source_file_path=str(source_path.absolute()),
            source_total_words=total_words,
            adaptation_format=AdaptationFormat(adaptation_format),
            target_episodes=target_episodes,
            episode_duration_min=episode_duration,
            genre=GenreType(genre),
            target_audience=target_audience,
            adaptation_direction=adaptation_direction,
            model_tier=ModelTier(model_tier),
            model_name=model_name,
            workspace_dir=str(project_dir.absolute()),
            asset_dir=str(asset_dir.absolute()),
            work_dir=str(work_dir.absolute()),
        )

        # 初始化数据库
        db_path = project_dir / "db.sqlite"
        init_db(db_path)

        # 保存项目记录
        with get_session() as session:
            repo = ProjectRepository(session)
            record = ProjectRecord(
                project_id=project_id,
                project_name=project_name,
                config_json=config.model_dump(mode="json"),
                status="initialized",
            )
            repo.create(record)

        # 初始化 ChromaDB
        chroma_dir = project_dir / "chroma"
        chroma = ChromaStore(persist_dir=chroma_dir)
        chroma.create_collection(project_id)

        return {
            "project_id": project_id,
            "workspace_dir": str(project_dir.absolute()),
            "project_config": config.model_dump(mode="json"),
            "total_words": total_words,
            "status": "initialized",
        }

    def _archive_scene(self, project_id: str, scene_id: str, script_data: dict) -> dict:
        """N15: 单场剧本入库"""
        from src.db.engine import get_session
        from src.db.repository import ScriptRepository
        from src.db.models import ScriptRecord

        with get_session() as session:
            repo = ScriptRepository(session)
            record = ScriptRecord(
                script_id=f"SCRIPT-{scene_id}-v1.0",
                project_id=project_id,
                scene_id=scene_id,
                episode_id=script_data.get("meta", {}).get("scene_id", "").split("-")[0],
                version="1.0",
                status="validated",
                script_json=script_data,
            )
            repo.create(record)

        return {"status": "archived", "script_id": record.script_id}

    def _stitch_episode(self, project_id: str, episode_id: str) -> dict:
        """N16: 单集剧本拼接"""
        from src.db.engine import get_session
        from src.db.repository import ScriptRepository

        with get_session() as session:
            repo = ScriptRepository(session)
            scripts = repo.list_by_episode(project_id, episode_id)

        if not scripts:
            return {"status": "error", "message": f"未找到 {episode_id} 的剧本"}

        scenes = [s.script_json for s in sorted(scripts, key=lambda s: s.scene_id)]
        return {
            "status": "stitched",
            "episode_id": episode_id,
            "scene_count": len(scenes),
            "scenes": scenes,
        }

    def _archive_project(self, project_id: str) -> dict:
        """N21: 项目结项归档"""
        from src.db.engine import get_session
        from src.db.repository import ProjectRepository

        with get_session() as session:
            repo = ProjectRepository(session)
            repo.update_status(project_id, "archived")

        return {"status": "archived", "project_id": project_id}

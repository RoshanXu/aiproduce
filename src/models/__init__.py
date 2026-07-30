"""数据模型层

Pydantic models 定义全系统核心数据结构：
- project: 项目配置
- asset: 人物/世界观/时间线资产
- chunk: 语义块与分层摘要
- outline: 大纲与场次
- script: 剧本
"""

from src.models.project import ProjectConfig, AdaptationFormat, GenreType, ModelTier
from src.models.asset import (
    CharacterAsset, WorldAsset, TimelineAsset, AssetLibrary,
    WorldSetting, CultureDetails, SceneAsset,
    TimelineEvent, ForeshadowEntry,
)
from src.models.chunk import (
    SemanticChunk, ChunkTag, ChunkTagType,
    ChapterSummary, StoryUnitSummary, GlobalSummary,
)
from src.models.outline import (
    EpisodeOutline, SeriesOutline, SceneCard, EpisodeSceneList,
)
from src.models.script import (
    ScriptMeta, SceneDescription, ScriptAction, ScriptLine,
    ScriptTransition, SceneScript, EpisodeScript, FullScript,
)

__all__ = [
    "ProjectConfig", "AdaptationFormat", "GenreType", "ModelTier",
    "CharacterAsset", "WorldAsset", "TimelineAsset", "AssetLibrary",
    "WorldSetting", "CultureDetails", "SceneAsset",
    "TimelineEvent", "ForeshadowEntry",
    "SemanticChunk", "ChunkTag", "ChunkTagType",
    "ChapterSummary", "StoryUnitSummary", "GlobalSummary",
    "EpisodeOutline", "SeriesOutline", "SceneCard", "EpisodeSceneList",
    "ScriptMeta", "SceneDescription", "ScriptAction", "ScriptLine",
    "ScriptTransition", "SceneScript", "EpisodeScript", "FullScript",
]
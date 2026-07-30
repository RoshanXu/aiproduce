"""核心项目配置模型"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class AdaptationFormat(str, Enum):
    SHORT_DRAMA = "短剧"
    WEB_SERIES = "网剧"
    ANIMATION = "漫剧"


class GenreType(str, Enum):
    HISTORICAL = "古装"
    MODERN = "现代"
    FANTASY = "架空"
    URBAN = "都市"
    SUSPENSE = "悬疑"
    SCI_FI = "科幻"
    ROMANCE = "言情"


class ModelTier(str, Enum):
    TIER_8K = "8K"
    TIER_32K = "32K"
    TIER_128K = "128K+"


class ProjectConfig(BaseModel):
    """项目配置"""
    project_id: str = Field(description="唯一项目标识")
    project_name: str = Field(description="项目名称")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 原著信息
    source_file_path: str = Field(description="原著文件路径")
    source_total_words: int = Field(default=0, description="原著总字数")

    # 改编配置
    adaptation_format: AdaptationFormat = Field(description="改编形式")
    target_episodes: int = Field(description="目标集数")
    episode_duration_min: int = Field(description="单集时长（分钟）")
    genre: GenreType = Field(description="题材类型")
    target_audience: str = Field(default="18-35岁", description="目标受众")
    adaptation_direction: str = Field(default="", description="核心改编方向")

    # 模型配置
    model_tier: ModelTier = Field(default=ModelTier.TIER_32K, description="选用模型档次")
    model_name: str = Field(default="claude-sonnet-5", description="具体模型名称")

    # 工作区路径（运行时填充）
    workspace_dir: str = Field(default="", description="项目工作区路径")
    asset_dir: str = Field(default="", description="资产库路径")
    work_dir: str = Field(default="", description="可写工作层路径")

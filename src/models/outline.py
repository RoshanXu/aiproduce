"""大纲与场次模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EpisodeOutline(BaseModel):
    """单集大纲"""
    episode_id: str = Field(description="集数标识")
    episode_number: int = Field(description="集号")
    act: str = Field(description="所属幕: 第一幕/第二幕/第三幕")
    core_conflict: str = Field(description="本集核心冲突")
    hook: str = Field(description="结尾钩子（悬念/情绪/信息/动作）")
    hook_type: str = Field(default="悬念", description="钩子类型")
    hook_rating: str = Field(default="B", description="钩子强度 A/B/C/D")

    # 多线占比
    main_plot_ratio: float = Field(default=60.0, description="主线占比%")
    subplot_ratios: dict[str, float] = Field(default_factory=dict, description="支线占比")

    # 关键节点
    key_turning_points: list[str] = Field(default_factory=list, description="关键转折点")
    character_growth_nodes: list[str] = Field(default_factory=list, description="人物成长节点")
    foreshadow_planting: list[str] = Field(default_factory=list, description="伏笔埋设点")

    summary: str = Field(default="", description="本集内容摘要")


class SeriesOutline(BaseModel):
    """全剧分集大纲"""
    total_episodes: int = Field(description="总集数")
    acts: dict[str, list[int]] = Field(default_factory=dict, description="三幕式集数划分")
    episodes: list[EpisodeOutline] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class SceneCard(BaseModel):
    """场次卡片"""
    scene_id: str = Field(description="场次唯一标识")
    scene_number: int = Field(description="场次序号")
    episode_id: str = Field(description="所属剧集")
    narrative_function: str = Field(description="叙事功能: 推进剧情/塑造人物/铺垫伏笔/制造冲突/过渡衔接/情绪释放")
    core_info_increment: str = Field(description="本场核心信息增量")

    # 出场信息
    characters_in_scene: list[str] = Field(default_factory=list, description="出场人物ID列表")
    scene_location: str = Field(description="场景地点")
    scene_time: str = Field(description="场景时间（日/夜/晨/昏）")

    # 结构
    opening: str = Field(default="", description="开场状态")
    development: str = Field(default="", description="发展过程")
    climax: str = Field(default="", description="本场高潮/转折")
    closing: str = Field(default="", description="收尾状态与钩子")

    # 原文锚点
    source_chapter: str = Field(default="", description="对应原著章节")
    source_chunk_ids: list[str] = Field(default_factory=list, description="对应语义块ID列表")

    status: str = Field(default="pending", description="状态: pending/writing/completed/validated")
    created_at: datetime = Field(default_factory=datetime.now)


class EpisodeSceneList(BaseModel):
    """单集场次清单"""
    episode_id: str
    episode_number: int
    scenes: list[SceneCard] = Field(default_factory=list)
    total_scenes: int = Field(default=0)

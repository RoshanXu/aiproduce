"""资产模型：人物、世界观、时间线"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ─── 人物资产 ───────────────────────────────────────────

class CharacterAsset(BaseModel):
    """人物资产"""
    char_id: str = Field(description="唯一标识，如 CHAR-001")
    name: str = Field(description="人物姓名")
    aliases: list[str] = Field(default_factory=list, description="别名列表")
    core_identity: str = Field(description="核心身份与开篇定位")
    appearance: Optional[str] = Field(default=None, description="外貌特征")
    core_personality: str = Field(description="核心性格特质与行为模式")
    speech_style: Optional[str] = Field(default=None, description="语言风格与台词特点")
    key_experiences: str = Field(description="影响人物的核心过往事件")
    core_goal: str = Field(description="核心诉求与终极目标")
    relationships: dict[str, str] = Field(default_factory=dict, description="与其他核心人物的关系 {人物ID: 关系描述}")
    character_arc: Optional[str] = Field(default=None, description="从开篇到结局的性格/身份变化")
    signature_behaviors: Optional[str] = Field(default=None, description="标志性习惯动作/偏好")
    conflicts: Optional[str] = Field(default=None, description="原著中存在的设定矛盾点")

    # 版本管理
    version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ─── 世界观资产 ───────────────────────────────────────────

class WorldSetting(BaseModel):
    """世界设定"""
    era_background: str = Field(description="时代背景")
    geography: str = Field(description="地理疆域")
    core_factions: list[str] = Field(default_factory=list, description="核心势力")
    social_hierarchy: str = Field(description="社会阶层与权力体系")
    universal_rules: str = Field(description="通用规则（阶级制度/权力体系/特殊能力等）")


class CultureDetails(BaseModel):
    """文化细节"""
    costume_rules: Optional[str] = Field(default=None, description="服饰规制")
    food_and_items: Optional[str] = Field(default=None, description="饮食器物")
    etiquette_and_titles: Optional[str] = Field(default=None, description="礼仪称谓")
    customs_and_institutions: Optional[str] = Field(default=None, description="习俗制度")


class SceneAsset(BaseModel):
    """场景资产"""
    scene_id: str = Field(description="场景唯一标识，如 SCENE-001")
    scene_name: str = Field(description="场景名称")
    space_type: str = Field(description="空间类型（室内/室外/复合）")
    visual_features: str = Field(description="视觉特征与氛围基调")
    appearance_chapters: list[int] = Field(default_factory=list, description="出现章节列表")
    core_function: str = Field(description="场景在剧情中的核心功能")


class WorldAsset(BaseModel):
    """世界观资产库"""
    basic_settings: WorldSetting = Field(description="基础设定")
    culture_details: CultureDetails = Field(description="文化细节")
    core_scenes: list[SceneAsset] = Field(default_factory=list, description="核心场景库")

    version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ─── 时间线资产 ───────────────────────────────────────────

class TimelineEvent(BaseModel):
    """时间线事件"""
    event_id: str = Field(description="事件唯一标识")
    time_point: str = Field(description="时间节点（绝对/相对）")
    time_confidence: str = Field(default="exact", description="时间置信度: exact/estimated/fuzzy")
    event_description: str = Field(description="核心事件描述")
    involved_characters: list[str] = Field(default_factory=list, description="涉及人物ID列表")
    location: str = Field(default="", description="发生地点")
    event_impact: str = Field(default="", description="事件影响")


class ForeshadowEntry(BaseModel):
    """伏笔条目"""
    foreshadow_id: str = Field(description="伏笔唯一标识")
    plant_chapter: int = Field(description="埋设章节")
    plant_content: str = Field(description="伏笔内容")
    payoff_chapter: Optional[int] = Field(default=None, description="回收章节")
    payoff_method: Optional[str] = Field(default=None, description="回收方式")
    status: str = Field(default="pending", description="状态: pending/resolved/unresolved")


class TimelineAsset(BaseModel):
    """时间线资产"""
    main_timeline: list[TimelineEvent] = Field(default_factory=list, description="主线时间轴")
    sub_timelines: dict[str, list[TimelineEvent]] = Field(default_factory=dict, description="支线时间轴")
    foreshadow_table: list[ForeshadowEntry] = Field(default_factory=list, description="伏笔回收对照表")

    version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ─── 资产库汇总 ───────────────────────────────────────────

class AssetLibrary(BaseModel):
    """完整的官方资产库"""
    version: str = Field(default="1.0")
    characters: list[CharacterAsset] = Field(default_factory=list)
    world: Optional[WorldAsset] = Field(default=None)
    timeline: Optional[TimelineAsset] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

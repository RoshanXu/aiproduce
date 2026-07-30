"""语义块与摘要模型"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class ChunkTagType(str, Enum):
    CHARACTER = "出场人物"
    EVENT = "关键事件"
    LOCATION = "场景地点"
    FORESHADOW = "伏笔埋设"
    WORLD_DETAIL = "世界观细节"


class ChunkTag(BaseModel):
    """语义块标签"""
    tag_type: ChunkTagType
    content: str = Field(description="标签内容")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="提取置信度")


class SemanticChunk(BaseModel):
    """语义块"""
    chunk_id: str = Field(description="语义块唯一标识")
    chunk_order: int = Field(description="语义块序号")

    # 所属信息
    volume: str = Field(default="", description="所属卷/部")
    chapter: str = Field(description="所属章节")
    story_unit: str = Field(default="", description="所属剧情单元")

    # 内容
    raw_text: str = Field(description="原始文本内容")
    word_count: int = Field(default=0, description="字数")
    summary: str = Field(description="块级摘要")

    # 边界信息
    boundary_type: str = Field(description="拆分边界类型: chapter/scene/time_jump/character_switch/plot_closure/dialogue_end")
    prev_chunk_id: Optional[str] = Field(default=None, description="前一块ID")
    next_chunk_id: Optional[str] = Field(default=None, description="后一块ID")

    # 元信息
    core_characters: list[str] = Field(default_factory=list, description="核心出场人物")
    core_scene: str = Field(default="", description="核心场景")
    event_type: str = Field(default="", description="核心事件类型")
    tags: list[ChunkTag] = Field(default_factory=list, description="五类基础标签")

    created_at: datetime = Field(default_factory=datetime.now)


class ChapterSummary(BaseModel):
    """章节摘要"""
    chapter_id: str
    chapter_title: str = Field(default="")
    summary: str = Field(description="章节结构化摘要")
    key_characters: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    key_locations: list[str] = Field(default_factory=list)
    foreshadows: list[str] = Field(default_factory=list)
    world_details: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list, description="关联语义块ID列表")


class StoryUnitSummary(BaseModel):
    """剧情单元摘要"""
    unit_id: str
    unit_name: str = Field(default="")
    summary: str
    chapters: list[str] = Field(default_factory=list)
    key_characters: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)


class GlobalSummary(BaseModel):
    """全局故事摘要"""
    full_summary: str = Field(description="全局故事完整摘要")
    main_conflict: str = Field(default="", description="核心冲突")
    theme_keywords: list[str] = Field(default_factory=list, description="主题关键词")
    total_chapters: int = Field(default=0)
    total_chunks: int = Field(default=0)
    total_characters: int = Field(default=0)

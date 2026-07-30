"""剧本模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ScriptMeta(BaseModel):
    """剧本元信息"""
    scene_id: str = Field(description="场次编号")
    scene_location: str = Field(description="场景")
    scene_time: str = Field(description="时间（日/夜/晨/昏）")
    characters_in_scene: str = Field(description="出场人物")


class SceneDescription(BaseModel):
    """场景描写"""
    content: str = Field(description="空间环境、光线、气氛，可拍摄的视觉元素")
    time_relation: Optional[str] = Field(default=None, description="与前场的时间关系")


class ScriptAction(BaseModel):
    """动作描写"""
    prefix: str = Field(default="▲", description="动作标记")
    content: str = Field(description="人物外部动作")


class ScriptLine(BaseModel):
    """台词"""
    character: str = Field(description="角色名")
    content: str = Field(description="台词内容")
    performance_note: Optional[str] = Field(default=None, description="表演提示（◎）")


class ScriptTransition(BaseModel):
    """转场"""
    prefix: str = Field(default="★", description="转场标记")
    transition_type: str = Field(description="切/淡入淡出/叠化/声音转场")


class SceneScript(BaseModel):
    """单场剧本"""
    meta: ScriptMeta = Field(description="元信息")
    scene_description: SceneDescription = Field(description="场景描写")
    body: list[ScriptAction | ScriptLine] = Field(default_factory=list, description="正文（动作+台词）")
    transition: Optional[ScriptTransition] = Field(default=None, description="转场标记")

    # 自检
    info_increment_check: str = Field(default="", description="观众本场获得的新信息")
    character_state_change: Optional[str] = Field(default=None, description="人物状态变化")
    foreshadow_notes: Optional[str] = Field(default=None, description="伏笔埋设/回收")

    # 改编说明
    adaptation_notes: Optional[str] = Field(default=None, description="原文心理内容→转化逻辑说明")

    # 版本管理
    version: str = Field(default="1.0")
    status: str = Field(default="draft", description="draft/validated/final")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class EpisodeScript(BaseModel):
    """单集剧本（多场拼接）"""
    episode_id: str
    episode_number: int
    scenes: list[SceneScript] = Field(default_factory=list)
    optimized_version: Optional[str] = Field(default=None, description="统稿优化版本")


class FullScript(BaseModel):
    """全剧剧本"""
    project_id: str
    episodes: list[EpisodeScript] = Field(default_factory=list)
    final_version: Optional[str] = Field(default=None, description="终稿版本")

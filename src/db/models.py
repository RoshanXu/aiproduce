"""SQLAlchemy ORM 模型

将 Pydantic 模型映射为 SQLite 持久化表。
使用 JSON 字段存储复杂嵌套结构，字符字段存储核心检索字段。
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ─── 项目表 ───────────────────────────────────────

class ProjectRecord(Base):
    __tablename__ = "projects"

    project_id = Column(String(64), primary_key=True)
    project_name = Column(String(256), nullable=False)
    config_json = Column(JSON, nullable=False, comment="完整 ProjectConfig JSON")
    status = Column(String(32), default="initialized")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ─── 资产表 ───────────────────────────────────────

class CharacterRecord(Base):
    __tablename__ = "characters"

    char_id = Column(String(32), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    name = Column(String(128), nullable=False)
    aliases_json = Column(JSON, default=[])
    core_identity = Column(Text, default="")
    core_personality = Column(Text, default="")
    speech_style = Column(Text, nullable=True)
    asset_json = Column(JSON, nullable=False, comment="完整 CharacterAsset JSON")
    version = Column(String(16), default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorldRecord(Base):
    __tablename__ = "world"

    world_id = Column(String(32), primary_key=True, default="WORLD-001")
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    era_background = Column(Text, default="")
    geography = Column(Text, default="")
    asset_json = Column(JSON, nullable=False, comment="完整 WorldAsset JSON")
    version = Column(String(16), default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TimelineRecord(Base):
    __tablename__ = "timeline"

    timeline_id = Column(String(32), primary_key=True, default="TL-001")
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    asset_json = Column(JSON, nullable=False, comment="完整 TimelineAsset JSON")
    version = Column(String(16), default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ─── 语义块与摘要表 ──────────────────────────────────

class ChunkRecord(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    chapter = Column(String(128), nullable=False)
    chunk_order = Column(Integer, nullable=False)
    word_count = Column(Integer, default=0)
    summary = Column(Text, default="")
    core_characters_json = Column(JSON, default=[])
    core_scene = Column(String(256), default="")
    event_type = Column(String(128), default="")
    tags_json = Column(JSON, default=[])
    chunk_json = Column(JSON, nullable=False, comment="完整 SemanticChunk JSON")
    created_at = Column(DateTime, default=datetime.now)


class SummaryRecord(Base):
    __tablename__ = "summaries"

    summary_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    summary_type = Column(String(32), nullable=False, comment="chapter/unit/global")
    level = Column(String(32), nullable=False, comment="章节级/单元级/全局级")
    summary_json = Column(JSON, nullable=False, comment="完整摘要 JSON")
    created_at = Column(DateTime, default=datetime.now)


# ─── 大纲与场次表 ──────────────────────────────────

class OutlineRecord(Base):
    __tablename__ = "outlines"

    outline_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    episode_number = Column(Integer, nullable=False)
    outline_json = Column(JSON, nullable=False, comment="完整 EpisodeOutline JSON")
    version = Column(String(16), default="1.0")
    created_at = Column(DateTime, default=datetime.now)


class SceneCardRecord(Base):
    __tablename__ = "scene_cards"

    scene_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    episode_id = Column(String(64), nullable=False)
    scene_number = Column(Integer, nullable=False)
    narrative_function = Column(String(64), default="")
    scene_json = Column(JSON, nullable=False, comment="完整 SceneCard JSON")
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.now)


# ─── 剧本表 ───────────────────────────────────────

class ScriptRecord(Base):
    __tablename__ = "scripts"

    script_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id"), nullable=False)
    scene_id = Column(String(64), nullable=False)
    episode_id = Column(String(64), nullable=False)
    version = Column(String(16), default="1.0")
    status = Column(String(32), default="draft")
    script_json = Column(JSON, nullable=False, comment="完整 SceneScript JSON")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

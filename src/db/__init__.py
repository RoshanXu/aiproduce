"""数据库层

SQLAlchemy ORM 模型 + Repository 模式封装：

使用方式：
    from src.db.engine import get_session
    from src.db.repository import CharacterRepository

    with get_session() as session:
        repo = CharacterRepository(session)
        char = repo.get_by_id("CHAR-001")
"""

from src.db.engine import DatabaseEngine, get_session, init_db
from src.db.models import (
    Base, ProjectRecord, CharacterRecord, WorldRecord, TimelineRecord,
    ChunkRecord, SummaryRecord, OutlineRecord, SceneCardRecord, ScriptRecord,
)
from src.db.repository import (
    ProjectRepository, CharacterRepository, WorldRepository,
    TimelineRepository, ChunkRepository, SummaryRepository,
    OutlineRepository, SceneCardRepository, ScriptRepository,
)

__all__ = [
    "DatabaseEngine", "get_session", "init_db",
    "Base", "ProjectRecord", "CharacterRecord", "WorldRecord",
    "TimelineRecord", "ChunkRecord", "SummaryRecord",
    "OutlineRecord", "SceneCardRecord", "ScriptRecord",
    "ProjectRepository", "CharacterRepository", "WorldRepository",
    "TimelineRepository", "ChunkRepository", "SummaryRepository",
    "OutlineRepository", "SceneCardRepository", "ScriptRepository",
]
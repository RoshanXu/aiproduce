"""Repository 模式 CRUD 封装

每个 Repository 对应一张表，提供类型安全的 CRUD 操作。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from src.db.models import (
    ProjectRecord, CharacterRecord, WorldRecord, TimelineRecord,
    ChunkRecord, SummaryRecord, OutlineRecord, SceneCardRecord, ScriptRecord,
)


class BaseRepository:
    """Repository 基类"""

    def __init__(self, session: Session):
        self.session = session

    def _update_timestamp(self, record):
        record.updated_at = datetime.now()


class ProjectRepository(BaseRepository):
    model = ProjectRecord

    def create(self, record: ProjectRecord) -> ProjectRecord:
        self.session.add(record)
        return record

    def get(self, project_id: str) -> Optional[ProjectRecord]:
        return self.session.get(self.model, project_id)

    def update_status(self, project_id: str, status: str):
        record = self.get(project_id)
        if record:
            record.status = status
            self._update_timestamp(record)


class CharacterRepository(BaseRepository):
    model = CharacterRecord

    def create(self, record: CharacterRecord) -> CharacterRecord:
        self.session.add(record)
        return record

    def get(self, char_id: str) -> Optional[CharacterRecord]:
        return self.session.get(self.model, char_id)

    def list_by_project(self, project_id: str) -> list[CharacterRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).all()

    def delete_by_project(self, project_id: str):
        self.session.query(self.model).filter_by(project_id=project_id).delete()


class WorldRepository(BaseRepository):
    model = WorldRecord

    def create(self, record: WorldRecord) -> WorldRecord:
        self.session.add(record)
        return record

    def get_by_project(self, project_id: str) -> Optional[WorldRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).first()

    def list_by_project(self, project_id: str) -> list[WorldRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).all()


class TimelineRepository(BaseRepository):
    model = TimelineRecord

    def create(self, record: TimelineRecord) -> TimelineRecord:
        self.session.add(record)
        return record

    def get_by_project(self, project_id: str) -> Optional[TimelineRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).first()

    def list_by_project(self, project_id: str) -> list[TimelineRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).all()


class ChunkRepository(BaseRepository):
    model = ChunkRecord

    def create(self, record: ChunkRecord) -> ChunkRecord:
        self.session.add(record)
        return record

    def create_batch(self, records: list[ChunkRecord]) -> list[ChunkRecord]:
        self.session.add_all(records)
        return records

    def get(self, chunk_id: str) -> Optional[ChunkRecord]:
        return self.session.get(self.model, chunk_id)

    def list_by_project(self, project_id: str) -> list[ChunkRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id
        ).order_by(self.model.chunk_order).all()

    def list_by_chapter(self, project_id: str, chapter: str) -> list[ChunkRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id, chapter=chapter
        ).order_by(self.model.chunk_order).all()

    def delete_by_project(self, project_id: str):
        self.session.query(self.model).filter_by(project_id=project_id).delete()


class SummaryRepository(BaseRepository):
    model = SummaryRecord

    def create(self, record: SummaryRecord) -> SummaryRecord:
        self.session.add(record)
        return record

    def get_by_type(self, project_id: str, summary_type: str) -> Optional[SummaryRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id, summary_type=summary_type
        ).first()

    def list_by_project(self, project_id: str) -> list[SummaryRecord]:
        return self.session.query(self.model).filter_by(project_id=project_id).all()


class OutlineRepository(BaseRepository):
    model = OutlineRecord

    def create(self, record: OutlineRecord) -> OutlineRecord:
        self.session.add(record)
        return record

    def create_batch(self, records: list[OutlineRecord]) -> list[OutlineRecord]:
        self.session.add_all(records)
        return records

    def list_by_project(self, project_id: str) -> list[OutlineRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id
        ).order_by(self.model.episode_number).all()

    def delete_by_project(self, project_id: str):
        self.session.query(self.model).filter_by(project_id=project_id).delete()


class SceneCardRepository(BaseRepository):
    model = SceneCardRecord

    def create(self, record: SceneCardRecord) -> SceneCardRecord:
        self.session.add(record)
        return record

    def create_batch(self, records: list[SceneCardRecord]) -> list[SceneCardRecord]:
        self.session.add_all(records)
        return records

    def list_by_episode(self, project_id: str, episode_id: str) -> list[SceneCardRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id, episode_id=episode_id
        ).order_by(self.model.scene_number).all()

    def delete_by_project(self, project_id: str):
        self.session.query(self.model).filter_by(project_id=project_id).delete()


class ScriptRepository(BaseRepository):
    model = ScriptRecord

    def create(self, record: ScriptRecord) -> ScriptRecord:
        self.session.add(record)
        return record

    def get_by_scene(self, project_id: str, scene_id: str) -> Optional[ScriptRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id, scene_id=scene_id
        ).order_by(self.model.version.desc()).first()

    def list_by_episode(self, project_id: str, episode_id: str) -> list[ScriptRecord]:
        return self.session.query(self.model).filter_by(
            project_id=project_id, episode_id=episode_id
        ).order_by(self.model.scene_id).all()

    def delete_by_project(self, project_id: str):
        self.session.query(self.model).filter_by(project_id=project_id).delete()

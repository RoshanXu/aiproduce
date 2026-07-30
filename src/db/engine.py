"""数据库引擎与会话管理"""

from pathlib import Path
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager


class DatabaseEngine:
    """SQLite 数据库引擎单例"""

    _instance: "DatabaseEngine | None" = None
    _engine: Engine | None = None
    _session_factory: sessionmaker | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, db_path: str | Path):
        """初始化数据库连接"""
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,  # 防止 DetachedInstanceError
        )

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    def create_all(self):
        """创建所有表"""
        from src.db.models import Base
        Base.metadata.create_all(self.engine)

    def drop_all(self):
        """删除所有表（仅测试用）"""
        from src.db.models import Base
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()


# 全局便捷函数
_db = DatabaseEngine()


def init_db(db_path: str | Path):
    """初始化数据库并创建表"""
    _db.initialize(db_path)
    _db.create_all()


@contextmanager
def get_session():
    """获取数据库会话上下文管理器"""
    session = _db.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

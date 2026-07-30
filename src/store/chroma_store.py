"""ChromaDB 向量存储封装

用于语义块与原文片段的向量化检索。
"""

import json
from pathlib import Path
from typing import Optional
from chromadb import PersistentClient
from chromadb.config import Settings


class ChromaStore:
    """ChromaDB 封装

    提供语义块的向量化存储与相似度检索。
    每个项目有独立的 collection。
    """

    def __init__(self, persist_dir: str | Path):
        persist_dir = Path(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections: dict[str, str] = {}  # project_id -> collection_name

    def _collection_name(self, project_id: str) -> str:
        return f"chunks_{project_id}"

    def create_collection(self, project_id: str):
        """为项目创建语义块 collection"""
        name = self._collection_name(project_id)
        try:
            self._client.delete_collection(name)
        except Exception:
            pass
        self._client.create_collection(name=name)
        self._collections[project_id] = name

    def add_chunks(self, project_id: str, chunks: list[dict]):
        """批量添加语义块到向量库

        Args:
            project_id: 项目ID
            chunks: [{
                "chunk_id": str,
                "text": str (用于向量化的文本),
                "metadata": dict (元信息)
            }]
        """
        name = self._collection_name(project_id)
        collection = self._client.get_collection(name=name)

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(
        self,
        project_id: str,
        query: str,
        n_results: int = 5,
        filter_chapter: Optional[str] = None,
    ) -> list[dict]:
        """语义检索

        Args:
            project_id: 项目ID
            query: 查询文本
            n_results: 返回结果数
            filter_chapter: 可选，限定章节

        Returns:
            [{"chunk_id": str, "text": str, "metadata": dict, "distance": float}]
        """
        name = self._collection_name(project_id)
        collection = self._client.get_collection(name=name)

        where_filter = None
        if filter_chapter:
            where_filter = {"chapter": filter_chapter}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                formatted.append({
                    "chunk_id": chunk_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
        return formatted

    def get_chunk(self, project_id: str, chunk_id: str) -> Optional[dict]:
        """获取单个语义块"""
        name = self._collection_name(project_id)
        collection = self._client.get_collection(name=name)
        result = collection.get(ids=[chunk_id])
        if result["ids"]:
            return {
                "chunk_id": result["ids"][0],
                "text": result["documents"][0] if result["documents"] else "",
                "metadata": result["metadatas"][0] if result["metadatas"] else {},
            }
        return None

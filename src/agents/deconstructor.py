"""N02 原著解构Agent"""

import json
import re
from pathlib import Path
from typing import Optional

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import ChunkRepository, SummaryRepository
from src.db.models import ChunkRecord, SummaryRecord
from src.store.chroma_store import ChromaStore
from src.models.chunk import SemanticChunk, ChapterSummary, StoryUnitSummary, GlobalSummary
from src.utils.text_utils import load_novel, count_chinese_words, detect_chapter_boundaries
from src.utils.logger import node_logger


class DeconstructorAgent(AgentBase):
    """N02 原著解构Agent

    负责：语义块拆分 → 块级摘要 → 章节摘要 → 全局摘要 → 标签提取
    """

    node_id = "N02"
    node_name = "原著解构Agent"

    def __init__(self, model_name: str = "claude-sonnet-5", max_chunk_words: int = 6000):
        super().__init__(model_name=model_name, temperature=0.3)
        self.max_chunk_words = max_chunk_words
        self._load_prompt()

    def _load_prompt(self):
        """加载 Prompt 模板"""
        prompt_path = Path("config/prompts/02_deconstructor.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, source_file_path: str) -> dict:
        """执行完整原著解构流程

        Returns:
            {
                chunks: list[dict],
                chapter_summaries: list[dict],
                global_summary: dict,
                chunk_count: int,
                total_words: int,
            }
        """
        novel_text = load_novel(source_file_path)
        total_words = count_chinese_words(novel_text)

        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 1. 自动检测章节边界
            log.info("检测章节边界...")
            chapter_boundaries = detect_chapter_boundaries(novel_text)

            if not chapter_boundaries:
                # 无章节标记，整篇作为一个块处理
                chapter_boundaries = [{"title": "全文", "start": 0, "end": len(novel_text), "text": novel_text}]

            log.info(f"检测到 {len(chapter_boundaries)} 个章节")

            # 2. 逐章处理：拆分 + 标签 + 摘要
            all_chunks = []
            all_chapter_summaries = []

            for ch_idx, chapter in enumerate(chapter_boundaries):
                log.info(f"处理章节 {ch_idx+1}/{len(chapter_boundaries)}: {chapter['title']}")

                chapter_chunks = self._process_chapter(
                    project_id=project_id,
                    chapter_title=chapter["title"],
                    chapter_text=chapter["text"],
                    chapter_index=ch_idx,
                    global_chunk_offset=len(all_chunks),
                )
                all_chunks.extend(chapter_chunks)

                # 生成章节摘要
                chapter_summary = self._generate_chapter_summary(
                    project_id=project_id,
                    chapter_title=chapter["title"],
                    chunk_ids=[c["chunk_id"] for c in chapter_chunks],
                    chapters_summaries=[c["summary"] for c in chapter_chunks],
                )
                all_chapter_summaries.append(chapter_summary)

            # 3. 存储语义块到 SQLite + ChromaDB
            self._store_chunks(project_id, all_chunks)

            # 4. 存储章节摘要
            self._store_summaries(project_id, all_chapter_summaries, "chapter")

            # 5. 生成并存储全局摘要
            global_summary = self._generate_global_summary(
                project_id=project_id,
                chapter_summaries=all_chapter_summaries,
                total_chapters=len(chapter_boundaries),
                total_chunks=len(all_chunks),
            )
            self._store_summaries(project_id, [global_summary], "global")

            log.info(f"解构完成: {len(all_chunks)} 个语义块, {len(all_chapter_summaries)} 个章节摘要")

        return {
            "chunks": all_chunks,
            "chapter_summaries": all_chapter_summaries,
            "global_summary": global_summary,
            "chunk_count": len(all_chunks),
            "total_words": total_words,
            "chapter_count": len(chapter_boundaries),
        }

    def _process_chapter(
        self,
        project_id: str,
        chapter_title: str,
        chapter_text: str,
        chapter_index: int,
        global_chunk_offset: int,
    ) -> list[dict]:
        """处理单个章节：拆分为语义块并通过 LLM 提取标签和摘要"""
        word_count = count_chinese_words(chapter_text)

        # 判断是否需要拆分
        if word_count <= self.max_chunk_words:
            blocks = [chapter_text]
        else:
            # 用 LLM 进行语义拆分
            blocks = self._semantic_split(chapter_text)

        chunks = []
        for blk_idx, block_text in enumerate(blocks):
            chunk_order = global_chunk_offset + blk_idx + 1
            chunk_id = f"CHUNK-{chunk_order:04d}"

            # 通过 LLM 提取块级信息
            block_info = self._extract_block_info(
                block_text=block_text,
                chapter_title=chapter_title,
                chunk_id=chunk_id,
            )

            chunk_data = {
                "chunk_id": chunk_id,
                "chunk_order": chunk_order,
                "volume": "",
                "chapter": chapter_title,
                "story_unit": block_info.get("story_unit", chapter_title),
                "word_count": count_chinese_words(block_text),
                "boundary_type": "chapter" if blk_idx == 0 else "scene_break",
                "prev_chunk_id": f"CHUNK-{chunk_order - 1:04d}" if chunk_order > 1 else None,
                "next_chunk_id": f"CHUNK-{chunk_order + 1:04d}",
                "raw_text": block_text[:200] + ("..." if len(block_text) > 200 else ""),
                "summary": block_info.get("summary", ""),
                "core_characters": block_info.get("core_characters", []),
                "core_scene": block_info.get("core_scene", ""),
                "event_type": block_info.get("event_type", "日常/过渡"),
                "tags": block_info.get("tags", {}),
            }
            chunks.append(chunk_data)

        return chunks

    def _semantic_split(self, chapter_text: str) -> list[str]:
        """使用 LLM 进行语义拆分"""
        # 对于原型阶段，如果 LLM 调用成本太高，使用简单的段落边界检测
        # 按双换行符拆分作为朴素的场景分割
        paragraphs = re.split(r"\n\n+", chapter_text)

        blocks = []
        current_block = ""
        current_words = 0

        for para in paragraphs:
            para_words = count_chinese_words(para)
            if current_words + para_words > self.max_chunk_words and current_block:
                blocks.append(current_block.strip())
                current_block = para
                current_words = para_words
            else:
                current_block += "\n\n" + para if current_block else para
                current_words += para_words

        if current_block.strip():
            blocks.append(current_block.strip())

        return blocks if blocks else [chapter_text]

    def _extract_block_info(self, block_text: str, chapter_title: str, chunk_id: str) -> dict:
        """通过 LLM 提取语义块的结构化信息"""
        # 仅取文本前 3000 字送给 LLM 做分析（节省 token）
        analysis_text = block_text[:3000]

        prompt = f"""分析以下小说片段，提取结构化信息。

所属章节：{chapter_title}
语义块ID：{chunk_id}

小说文本：
---
{analysis_text}
---

请输出JSON格式（仅JSON，不要其他文字）：
{{
  "story_unit": "剧情单元名称（简短语义归纳）",
  "summary": "1-2句块级摘要",
  "core_characters": ["人物1", "人物2"],
  "core_scene": "具体地点",
  "event_type": "日常/过渡/遇袭/对话/转折/回忆/战斗/离别",
  "tags": {{
    "characters": "所有出场人物及其身份描述",
    "key_events": "本块关键事件",
    "location": "场景地点",
    "foreshadow": "可能的伏笔线索（无则填'无'）",
    "world_details": "世界观细节（无则填'无'）"
  }}
}}"""

        response = self.call_llm(user_input=prompt)
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise RuntimeError(f"LLM 返回格式异常，未找到有效 JSON: {response[:200]}")

    def _generate_chapter_summary(
        self, project_id: str, chapter_title: str,
        chunk_ids: list[str], chapters_summaries: list[str],
    ) -> dict:
        """生成章节摘要"""
        combined = " ".join(chapters_summaries)
        chapter_id = f"CH-{chapter_title.replace(' ', '-')}"

        return {
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "summary": combined[:500],
            "key_characters": [],
            "key_events": [],
            "key_locations": [],
            "foreshadows": [],
            "world_details": [],
            "chunk_ids": chunk_ids,
        }

    def _generate_global_summary(
        self, project_id: str, chapter_summaries: list[dict],
        total_chapters: int, total_chunks: int,
    ) -> dict:
        """生成全局摘要（聚合所有章节摘要）"""
        all_summaries = " ".join(cs["summary"] for cs in chapter_summaries)

        return {
            "chapter_id": "GLOBAL",
            "chapter_title": "全局摘要",
            "summary": all_summaries[:1000],
            "key_characters": [],
            "key_events": [],
            "key_locations": [],
            "foreshadows": [],
            "world_details": [],
            "chunk_ids": [],
        }

    # ─── 存储方法 ────────────────────────────

    def _store_chunks(self, project_id: str, chunks: list[dict]):
        """存储语义块到 SQLite + ChromaDB"""
        # SQLite
        with get_session() as session:
            repo = ChunkRepository(session)
            repo.delete_by_project(project_id)

            records = []
            for c in chunks:
                records.append(ChunkRecord(
                    chunk_id=c["chunk_id"],
                    project_id=project_id,
                    chapter=c["chapter"],
                    chunk_order=c["chunk_order"],
                    word_count=c["word_count"],
                    summary=c["summary"],
                    core_characters_json=c.get("core_characters", []),
                    core_scene=c.get("core_scene", ""),
                    event_type=c.get("event_type", ""),
                    tags_json=c.get("tags", {}),
                    chunk_json=c,
                ))
            repo.create_batch(records)

        # ChromaDB
        project_dir = Path("workspace/projects") / project_id
        chroma = ChromaStore(persist_dir=project_dir / "chroma")
        chroma_docs = []
        for c in chunks:
            chroma_docs.append({
                "chunk_id": c["chunk_id"],
                "text": c["raw_text"],
                "metadata": {
                    "chapter": c["chapter"],
                    "chunk_order": c["chunk_order"],
                    "core_characters": ", ".join(c.get("core_characters", [])),
                    "core_scene": c.get("core_scene", ""),
                    "event_type": c.get("event_type", ""),
                },
            })
        chroma.add_chunks(project_id, chroma_docs)

    def _store_summaries(self, project_id: str, summaries: list[dict], summary_type: str):
        """存储摘要到 SQLite"""
        with get_session() as session:
            repo = SummaryRepository(session)
            for s in summaries:
                record = SummaryRecord(
                    summary_id=f"SUM-{summary_type}-{s['chapter_id']}",
                    project_id=project_id,
                    summary_type=summary_type,
                    level="章节级" if summary_type == "chapter" else "全局级",
                    summary_json=s,
                )
                repo.create(record)

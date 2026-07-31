"""N03 人设资产管理Agent"""

import json
import re
from pathlib import Path
from typing import Optional

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import CharacterRepository, ChunkRepository
from src.db.models import CharacterRecord
from src.utils.logger import node_logger


class CharacterAssetAgent(AgentBase):
    """人设资产管理Agent

    负责 N03/N06：从语义块标签聚合人物资产库。
    """

    node_id = "N03"
    node_name = "人设资产管理Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.3)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/03_character_asset.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str) -> dict:
        """从语义块标签聚合人物资产库

        Args:
            project_id: 项目ID

        Returns:
            {characters: list[dict], top10_completeness: dict, total_characters: int}
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 1. 加载所有语义块的标签数据
            log.info("加载语义块标签...")
            with get_session() as session:
                chunk_repo = ChunkRepository(session)
                chunks = chunk_repo.list_by_project(project_id)

            if not chunks:
                log.warning("无语义块数据，返回空资产库")
                return {"characters": [], "top10_completeness": {}, "total_characters": 0}

            # 2. 聚合所有人物提及
            log.info("聚合人物信息...")
            character_mentions = self._aggregate_mentions(chunks)

            # 3. 尝试用 LLM 做深度聚合与字段补全
            characters = self._llm_build_characters(character_mentions, chunks[:20])

            # 4. 去重合并
            characters = self._deduplicate(characters)

            # 5. 存储到数据库
            log.info(f"存储 {len(characters)} 个人物到资产库...")
            self._store_characters(project_id, characters)

            # 6. 计算字段完整度
            completeness = self._calc_completeness(characters)

            log.info(f"人物资产库构建完成: {len(characters)} 个人物")

        return {
            "characters": characters,
            "top10_completeness": completeness,
            "total_characters": len(characters),
        }

    def _aggregate_mentions(self, chunks: list) -> dict[str, dict]:
        """从语义块中聚合人物提及信息"""
        mentions: dict[str, dict] = {}

        for chunk in chunks:
            tags = chunk.tags_json or {}
            char_tag = tags.get("characters", "")
            event_type = chunk.event_type or ""
            summary = chunk.summary or ""

            # 从角色标签中提取角色名
            if char_tag and char_tag != "待提取":
                # 按顿号、逗号或"、"分割
                names = re.split(r"[，,、]", str(char_tag))
                for name in names:
                    name = name.strip()
                    if not name or len(name) < 2:
                        continue

                    # 提取括号中的描述
                    desc_match = re.search(r"[（(](.*?)[）)]", name)
                    description = desc_match.group(1) if desc_match else ""
                    clean_name = re.sub(r"[（(].*?[）)]", "", name).strip()

                    if clean_name not in mentions:
                        mentions[clean_name] = {
                            "name": clean_name,
                            "aliases": set(),
                            "appearances": [],
                            "descriptions": [],
                        }

                    mentions[clean_name]["appearances"].append({
                        "chunk_id": chunk.chunk_id,
                        "chapter": chunk.chapter,
                        "event_type": event_type,
                        "summary": summary,
                    })
                    if description:
                        mentions[clean_name]["descriptions"].append(description)

            # 也从 core_characters 提取
            core_chars = chunk.core_characters_json or []
            for name in core_chars:
                if name not in mentions:
                    mentions[name] = {
                        "name": name,
                        "aliases": set(),
                        "appearances": [],
                        "descriptions": [],
                    }

        return mentions

    def _llm_build_characters(self, mentions: dict, sample_chunks: list) -> list[dict]:
        """使用 LLM 做深度人物档案构建"""
        # 构建简要的输入上下文
        mention_summary = []
        for name, info in list(mentions.items())[:30]:  # 限制数量
            appearances = info["appearances"][:3]  # 每人最多3次出场
            summary_texts = "；".join(a["summary"][:100] for a in appearances)
            descs = "；".join(info["descriptions"][:3])
            mention_summary.append(
                f"- {name}：{descs} | 出场：{summary_texts}"
            )

        prompt = f"""基于以下人物出场信息，构建标准人物档案。

人物出场信息：
{chr(10).join(mention_summary)}

请输出 JSON 格式（仅 JSON，不要其他文字）：
{{
  "characters": [
    {{
      "char_id": "CHAR-001",
      "name": "人物本名",
      "aliases": ["别名1", "别名2"],
      "core_identity": "开篇身份与定位",
      "appearance": "外貌特征（无则'待补充'）",
      "core_personality": "性格特质",
      "speech_style": "语言风格（无则'待补充'）",
      "key_experiences": "核心过往事件",
      "core_goal": "核心诉求",
      "relationships": {{"其他人物名": "关系描述"}},
      "character_arc": "预计弧光（无则'待补充'）",
      "signature_behaviors": "标志性行为（无则'待补充'）",
      "conflicts": null
    }}
  ]
}}"""

        import re as _re2
        response = self.call_llm(user_input=prompt)
        json_match = _re2.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("characters", result if isinstance(result, list) else [])
        raise RuntimeError("LLM 人物构建返回格式异常，未找到有效 JSON")

    def _deduplicate(self, characters: list[dict]) -> list[dict]:
        """去重合并（基于规则：名字相似度 + 身份重合度）"""
        # 原型阶段使用简单规则：完全相同名字的合并
        seen_names: dict[str, dict] = {}
        result = []

        for char in characters:
            name = char["name"]
            if name in seen_names:
                # 合并 aliases
                existing = seen_names[name]
                existing["aliases"] = list(set(existing.get("aliases", []) + char.get("aliases", [])))
                # 取信息更完整的
                for field in ["appearance", "core_personality", "speech_style", "core_goal", "character_arc"]:
                    if char.get(field) and char[field] != "待补充" and (not existing.get(field) or existing[field] == "待补充"):
                        existing[field] = char[field]
            else:
                seen_names[name] = char
                result.append(char)

        return result

    def _calc_completeness(self, characters: list[dict]) -> dict[str, float]:
        """计算人物档案字段完整度"""
        required_fields = ["name", "core_identity", "core_personality", "key_experiences", "core_goal"]
        optional_fields = ["appearance", "speech_style", "character_arc", "signature_behaviors"]

        completeness = {}
        for char in characters[:10]:
            required_filled = sum(1 for f in required_fields if char.get(f) and char[f] != "待补充")
            optional_filled = sum(1 for f in optional_fields if char.get(f) and char[f] != "待补充")
            total = len(required_fields) + len(optional_fields)
            filled = required_filled + optional_filled
            completeness[char["char_id"]] = round(filled / total, 2)

        return completeness

    def _store_characters(self, project_id: str, characters: list[dict]):
        """存储人物资产到 SQLite"""
        with get_session() as session:
            repo = CharacterRepository(session)
            repo.delete_by_project(project_id)

            for char in characters:
                record = CharacterRecord(
                    char_id=char["char_id"],
                    project_id=project_id,
                    name=char["name"],
                    aliases_json=char.get("aliases", []),
                    core_identity=char.get("core_identity", ""),
                    core_personality=char.get("core_personality", ""),
                    speech_style=char.get("speech_style"),
                    asset_json=char,
                    version="1.0",
                )
                repo.create(record)

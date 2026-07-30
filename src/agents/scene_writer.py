"""N11 单场剧本Agent"""

import json
import re
from pathlib import Path

from src.agents.base import AgentBase
from src.db.engine import get_session
from src.db.repository import CharacterRepository, ChunkRepository
from src.store.chroma_store import ChromaStore
from src.utils.logger import node_logger


class SceneWriterAgent(AgentBase):
    """单场剧本Agent — N11 单场剧本生成

    基于场次卡片、原文片段和人物设定，生成标准格式剧本。
    """

    node_id = "N11"
    node_name = "单场剧本Agent"

    def __init__(self, model_name: str = "claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.8)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/09_scene_writer.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, scene_card: dict) -> dict:
        """生成单场剧本

        Args:
            project_id: 项目ID
            scene_card: 场次卡片 dict

        Returns:
            {scene_id, script: dict} 单场剧本
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            scene_id = scene_card.get("scene_id", "unknown")

            # 加载上下文
            context = self._load_scene_context(project_id, scene_card)

            # 生成剧本
            if self.prompt_template:
                script = self._llm_write(context)
            else:
                script = self._template_write(context)

            # 保存
            self._save_script(project_id, scene_id, script)

            log.info(f"剧本生成: {scene_id}")

        return {"scene_id": scene_id, "script": script}

    def _load_scene_context(self, project_id: str, scene_card: dict) -> dict:
        """加载单场剧本所需的上下文"""
        context = dict(scene_card)

        with get_session() as session:
            # 出场人物设定
            char_ids = scene_card.get("characters_in_scene", [])
            char_repo = CharacterRepository(session)
            char_profiles = []
            for cid in char_ids:
                char = char_repo.get(cid)
                if char:
                    char_profiles.append({
                        "char_id": char.char_id,
                        "name": char.name,
                        "core_identity": char.core_identity,
                        "core_personality": char.core_personality,
                        "speech_style": char.speech_style or "待补充",
                        "signature_behaviors": char.asset_json.get("signature_behaviors", ""),
                    })
            context["character_profiles"] = char_profiles

            # 原文片段（从 ChromaDB 检索）
            chunk_ids = scene_card.get("source_chunk_ids", [])
            source_texts = []
            if chunk_ids:
                chroma_dir = Path("workspace/projects") / project_id / "chroma"
                chroma = ChromaStore(persist_dir=chroma_dir)
                for cid in chunk_ids:
                    chunk = chroma.get_chunk(project_id, cid)
                    if chunk:
                        source_texts.append(chunk.get("text", ""))
            context["source_text"] = "\n\n".join(source_texts[:3])

        return context

    def _llm_write(self, context: dict) -> dict:
        """LLM 生成剧本"""
        prompt = f"""基于以下场次信息，生成标准格式单场剧本。

## 场次信息
- 场次编号: {context.get('scene_id', '')}
- 叙事功能: {context.get('narrative_function', '')}
- 核心信息增量: {context.get('core_info_increment', '')}
- 场景地点: {context.get('scene_location', '')}
- 场景时间: {context.get('scene_time', '')}

## 出场人物设定
{json.dumps(context.get('character_profiles', []), ensure_ascii=False, indent=2)[:1500]}

## 原著参考片段
{context.get('source_text', '')[:1000]}

## 要求
严格遵循五条创作铁律：
1. 禁止心理描写（一切心理内容转化为外部动作）
2. 台词一人一声（每个角色有独特的说话方式）
3. 零静态情绪描写（每场至少2个实质性戏剧动作）
4. 每场必须有信息增量
5. 场景即叙事（通过场景互动展现人物状态）

输出标准格式剧本 JSON。
"""

        try:
            response = self.call_llm(user_input=prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            node_logger.warn(f"LLM 剧本生成失败: {e}")

        return self._template_write(context)

    def _template_write(self, context: dict) -> dict:
        """模板剧本（降级方案）"""
        scene_id = context.get("scene_id", "")
        chars = context.get("character_profiles", [])
        main_char = chars[0] if chars else {"name": "主角", "char_id": "CHAR-001"}

        body_lines = [
            {"prefix": "▲", "content": f"{main_char['name']}站在{context.get('scene_location', '场景')}中，环顾四周。手指无意识地敲击着腰间的剑柄。"},
            {"character": main_char['name'], "content": f"（低声）这里不对劲。", "performance_note": "警觉地环视"},
        ]

        if len(chars) > 1:
            second = chars[1]
            body_lines.append({"prefix": "▲", "content": f"{second['name']}走上前，与{main_char['name']}并肩而立。"})
            body_lines.append({"character": second['name'], "content": "少主，要不要我去查看？"})

        body_lines.append({"prefix": "▲", "content": f"{main_char['name']}抬手制止。目光锁定在前方的阴影处。"})
        body_lines.append({"prefix": "★", "transition_type": "切"})

        return {
            "meta": {
                "scene_id": scene_id,
                "scene_location": context.get("scene_location", "待设定"),
                "scene_time": context.get("scene_time", "日"),
                "characters_in_scene": ", ".join(c["name"] for c in chars),
            },
            "scene_description": {
                "content": f"{context.get('scene_location', '场景')}。{context.get('scene_time', '日')}光透过缝隙洒入，空气中弥漫着紧张的气息。",
                "time_relation": "承接前场，时间连续",
            },
            "body": body_lines,
            "transition": {"prefix": "★", "transition_type": "切"},
            "info_increment_check": context.get("core_info_increment", ""),
            "adaptation_notes": "（模板生成，待LLM精修）",
            "version": "1.0",
            "status": "draft",
        }

    def _save_script(self, project_id: str, scene_id: str, script: dict):
        """保存剧本"""
        output_dir = Path("workspace/projects") / project_id / "work" / "drafts"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{scene_id}.json").write_text(
            json.dumps(script, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

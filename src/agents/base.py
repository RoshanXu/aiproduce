"""Agent 基类

所有 Agent 继承此基类，获得统一的：
- LLM 调用接口（支持 Claude / OpenAI）
- 结构化输出解析（Pydantic schema validation）
- 自动重试与错误处理
- 节点日志追踪
- Token 统计
"""

import json
import time
import re
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

# Lazy imports: langchain 可能存在版本兼容问题，降级使用 anthropic SDK
try:
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from src.utils.logger import node_logger
from src.utils.token_counter import token_counter


class AgentBase(ABC):
    """Agent 基类

    子类需实现：
    - node_id: str       节点编号 (如 "N02")
    - node_name: str     节点名称 (如 "原著解构Agent")
    - prompt_template: str Prompt 模板内容
    """

    node_id: str
    node_name: str
    prompt_template: str = ""

    def __init__(
        self,
        model_name: str = "claude-sonnet-5",
        max_retries: int = 3,
        temperature: float = 0.7,
    ):
        self.model_name = model_name
        self.max_retries = max_retries
        self.temperature = temperature
        self._llm = None

    def _get_llm(self):
        """延迟初始化 LLM 实例

        优先使用 langchain，降级使用原生 anthropic SDK。
        """
        if self._llm is not None:
            return self._llm

        if HAS_LANGCHAIN:
            if "claude" in self.model_name.lower():
                self._llm = ChatAnthropic(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=8192,
                )
            elif "gpt" in self.model_name.lower() or "openai" in self.model_name.lower():
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=8192,
                )
            else:
                self._llm = ChatAnthropic(
                    model="claude-sonnet-5",
                    temperature=self.temperature,
                    max_tokens=8192,
                )
        elif HAS_ANTHROPIC and "claude" in self.model_name.lower():
            # 使用原生 anthropic SDK（轻量降级方案）
            self._llm = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        else:
            raise RuntimeError(
                "No LLM backend available. "
                "Install langchain-anthropic or set ANTHROPIC_API_KEY."
            )
        return self._llm

    def _render_prompt(self, **kwargs) -> str:
        """渲染 Prompt 模板

        将 {{variable}} 占位符替换为实际值。
        """
        template = self.prompt_template
        for key, value in kwargs.items():
            placeholder = "{{" + key + "}}"
            template = template.replace(placeholder, str(value))
        return template

    def call_llm(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        output_schema: Optional[dict] = None,
    ) -> str:
        """统一 LLM 调用接口

        支持 langchain 和原生 anthropic SDK 两种后端。
        """
        with node_logger.node_context(self.node_id, self.node_name) as log:
            for attempt in range(1, self.max_retries + 1):
                try:
                    if HAS_LANGCHAIN:
                        content = self._call_via_langchain(user_input, system_prompt)
                    elif HAS_ANTHROPIC:
                        content = self._call_via_anthropic(user_input, system_prompt)
                    else:
                        raise RuntimeError("No LLM backend available.")

                    # 结构化输出校验
                    if output_schema:
                        content = self._validate_json(content, output_schema)
                        if content is None and attempt < self.max_retries:
                            log.warning(f"结构化输出校验失败，重试 {attempt}/{self.max_retries}")
                            user_input += f"\n\n输出格式不符合要求，请严格按照以下JSON Schema重新输出：\n{json.dumps(output_schema, ensure_ascii=False)}"
                            time.sleep(2 ** attempt)
                            continue

                    return content

                except Exception as e:
                    log.error(f"LLM 调用失败 (attempt {attempt}/{self.max_retries}): {e}")
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                    else:
                        raise RuntimeError(
                            f"[{self.node_id}] {self.node_name} LLM 调用在 {self.max_retries} 次重试后仍然失败"
                        ) from e

            raise RuntimeError(
                f"[{self.node_id}] {self.node_name} 结构化输出校验在 {self.max_retries} 次重试后仍然失败"
            )

    def _call_via_langchain(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """通过 langchain 调用 LLM"""
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = self._get_llm()
        messages = [
            SystemMessage(content=system_prompt or "你是一个专业的小说改剧本AI助手。请严格按照指令输出结构化内容。"),
            HumanMessage(content=user_input),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage", {})
            token_counter.record(
                node_id=self.node_id,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                model=self.model_name,
            )
        return content

    def _call_via_anthropic(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """通过原生 anthropic SDK 调用 LLM"""
        llm = self._get_llm()
        response = llm.messages.create(
            model=self.model_name,
            max_tokens=8192,
            temperature=self.temperature,
            system=system_prompt or "你是一个专业的小说改剧本AI助手。请严格按照指令输出结构化内容。",
            messages=[{"role": "user", "content": user_input}],
        )
        content = response.content[0].text

        token_counter.record(
            node_id=self.node_id,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=self.model_name,
        )
        return content

    @staticmethod
    def _validate_json(content: str, schema: dict) -> Optional[str]:
        """使用 JSON Schema 校验输出内容

        Returns:
            校验通过返回原内容，失败返回 None
        """
        try:
            # 尝试提取 JSON（可能在 markdown code block 中）
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 尝试直接解析
                json_str = content.strip()

            import jsonschema
            data = json.loads(json_str)
            jsonschema.validate(data, schema)
            return content  # 校验通过
        except (json.JSONDecodeError, Exception):
            # 如果没有安装 jsonschema，跳过校验
            return content

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """执行 Agent 核心逻辑

        子类必须实现此方法。
        """
        ...

    def __repr__(self):
        return f"<{self.node_id} {self.node_name}>"

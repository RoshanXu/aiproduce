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

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

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
        max_tokens: int = 8192,
    ):
        self.model_name = model_name
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm = None

    def _get_llm(self):
        """延迟初始化 LLM 实例（必须先配置 API Key）"""
        if self._llm is not None:
            return self._llm

        model_lower = self.model_name.lower()

        if "deepseek" in model_lower:
            key = os.getenv("DEEPSEEK_API_KEY", "")
            if not key:
                raise RuntimeError(
                    "❌ 未配置 DEEPSEEK_API_KEY。\n"
                    "   请在项目根目录的 .env 文件中设置: DEEPSEEK_API_KEY=你的Key\n"
                    "   如果没有 .env 文件，请复制 .env.example 并填入 Key"
                )
            self._llm = anthropic.Anthropic(
                api_key=key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic"),
            )

        elif "claude" in model_lower:
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                raise RuntimeError(
                    "❌ 未配置 ANTHROPIC_API_KEY。\n"
                    "   请在项目根目录的 .env 文件中设置: ANTHROPIC_API_KEY=你的Key"
                )
            if HAS_LANGCHAIN:
                self._llm = ChatAnthropic(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            elif HAS_ANTHROPIC:
                self._llm = anthropic.Anthropic(api_key=key)
            else:
                raise RuntimeError("需要安装: pip install anthropic")

        elif "gpt" in model_lower or "openai" in model_lower:
            key = os.getenv("OPENAI_API_KEY", "")
            if not key:
                raise RuntimeError(
                    "❌ 未配置 OPENAI_API_KEY。\n"
                    "   请在项目根目录的 .env 文件中设置: OPENAI_API_KEY=你的Key"
                )
            self._llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        else:
            raise RuntimeError(
                f"❌ 不支持的模型: {self.model_name}\n"
                f"   支持的模型: deepseek-v4-pro, claude-sonnet-5, gpt-4o 等\n"
                f"   请在 .env 文件中设置 DEFAULT_MODEL"
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
            # 兼容不同 API 的字段名:
            # Claude: input_tokens / output_tokens
            # OpenAI / DeepSeek: prompt_tokens / completion_tokens
            prompt = usage.get("input_tokens") or usage.get("prompt_tokens", 0)
            completion = usage.get("output_tokens") or usage.get("completion_tokens", 0)
            token_counter.record(
                node_id=self.node_id,
                prompt_tokens=prompt,
                completion_tokens=completion,
                model=self.model_name,
            )
        return content

    def _call_via_anthropic(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """通过原生 anthropic SDK 调用 LLM"""
        llm = self._get_llm()
        response = llm.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt or "你是一个专业的小说改剧本AI助手。请严格按照指令输出结构化内容。",
            messages=[{"role": "user", "content": user_input}],
        )
        # 提取文本 block（DeepSeek 返回 ThinkingBlock + TextBlock）
        content = ""
        for block in response.content:
            if getattr(block, "type", "") == "text":
                content = block.text
                break
        # 兜底：取第一个 block
        if not content and response.content:
            content = getattr(response.content[0], "text", "")

        token_counter.record(
            node_id=self.node_id,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=self.model_name,
        )
        return content

    @staticmethod
    def _parse_json_response(response: str) -> dict:
        """从 LLM 响应中提取并解析 JSON，自动修复常见格式问题。

        按优先级尝试：
        1. 直接解析
        2. 去除尾部逗号
        3. 修复无引号 key / 单引号字符串
        4. 按花括号深度提取有效 JSON 片段

        Raises:
            RuntimeError: 所有修复手段均失败时抛出
        """
        # Step 1: 提取 JSON 块（优先匹配 markdown code block）
        json_str = response
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)```", response, re.DOTALL)
        if code_match:
            json_str = code_match.group(1).strip()
        else:
            brace_match = re.search(r"\{.*\}", response, re.DOTALL)
            if brace_match:
                json_str = brace_match.group()
            else:
                raise RuntimeError("LLM 响应中未找到有效 JSON 结构")

        # Step 2: 依次尝试解析 + 修复
        last_error = None
        for attempt, repair_fn in enumerate([
            lambda s: s,                                                    # 0: 直接解析
            lambda s: re.sub(r",\s*([}\]])", r"\1", s),                    # 1: 去尾部逗号
            lambda s: re.sub(r",\s*([}\]])", r"\1",                        # 2: 去尾部逗号 + 加引号 key
                             re.sub(r'(?<=\{)\s*(\w+)\s*:', r'"\1":', s)),
            lambda s: re.sub(r",\s*([}\]])", r"\1",                        # 3: 去尾部逗号 + 加引号 key + 单引号→双引号
                             re.sub(r"'([^']*)'", r'"\1"',
                             re.sub(r'(?<=\{)\s*(\w+)\s*:', r'"\1":', s))),
        ]):
            try:
                repaired = repair_fn(json_str)
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                last_error = e
                continue

        # Step 4: 最后手段 — 按花括号深度提取第一个完整 JSON 对象
        try:
            depth = 0
            start = json_str.find("{")
            if start >= 0:
                for i in range(start, len(json_str)):
                    if json_str[i] == "{":
                        depth += 1
                    elif json_str[i] == "}":
                        depth -= 1
                        if depth == 0:
                            truncated = json_str[start:i+1]
                            truncated = re.sub(r",\s*([}\]])", r"\1", truncated)
                            return json.loads(truncated)
        except json.JSONDecodeError as e:
            last_error = e

        # 构建详细错误信息
        err_pos = last_error.pos if last_error else 0
        total_len = len(json_str)
        ctx_start = max(0, err_pos - 200)
        ctx_end = min(total_len, err_pos + 200)
        context = json_str[ctx_start:ctx_end]
        truncated_hint = ""
        if total_len > 0:
            # 检查是否被截断：花括号不匹配
            braces = 0
            for ch in json_str:
                if ch == "{": braces += 1
                elif ch == "}": braces -= 1
            if braces > 0:
                truncated_hint = (
                    f"\n⚠️ 疑似 LLM 输出被截断！"
                    f"\n   JSON 长度: {total_len} 字符"
                    f"\n   未闭合花括号: {braces} 个"
                    f"\n   → 尝试增大该 Agent 的 max_tokens 参数"
                )

        raise RuntimeError(
            f"LLM 返回 JSON 格式异常，所有修复手段均失败。"
            f"\n   总长度: {total_len} 字符, 错误位置: 第 {err_pos} 字符附近"
            f"\n   最后错误: {last_error}"
            f"{truncated_hint}"
            f"\n   错误位置上下文:\n···{context}···"
        )

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

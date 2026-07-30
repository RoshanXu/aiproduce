"""Token 消耗统计

追踪每次 LLM 调用的 Token 消耗，支持按节点汇总统计和持久化。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TokenUsage:
    """单次调用 Token 使用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    node_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def estimated_cost_usd(self) -> float:
        """估算 API 成本（USD）

        使用 Claude Sonnet 定价作为参考:
        - 输入: $3/M tokens
        - 输出: $15/M tokens
        """
        input_cost = (self.prompt_tokens / 1_000_000) * 3.0
        output_cost = (self.completion_tokens / 1_000_000) * 15.0
        return round(input_cost + output_cost, 6)

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cost_usd": self.estimated_cost_usd,
        }


# 模型定价表 ($/M tokens)
MODEL_PRICING = {
    "claude-sonnet-5":     {"input": 3.0,  "output": 15.0},
    "claude-opus-5":       {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5":    {"input": 0.8,  "output": 4.0},
    "claude-fable-5":      {"input": 5.0,  "output": 25.0},
    "gpt-4o":              {"input": 2.5,  "output": 10.0},
    "gpt-4o-mini":         {"input": 0.15, "output": 0.6},
    "deepseek-v4-pro":     {"input": 0.5,  "output": 2.0},
}


class TokenCounter:
    """全局 Token 计数器（支持持久化）"""

    def __init__(self):
        self._records: list[TokenUsage] = []
        self._node_totals: dict[str, TokenUsage] = {}
        self._project_id: str | None = None
        self._persist_path: Path | None = None

    def set_project(self, project_id: str, workspace_dir: str | Path):
        """绑定到项目，启用持久化"""
        self._project_id = project_id
        self._persist_path = Path(workspace_dir) / "work" / "token_usage.jsonl"
        self._load_from_disk()

    def _load_from_disk(self):
        """从磁盘加载历史记录"""
        if self._persist_path and self._persist_path.exists():
            try:
                with open(self._persist_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self._apply_record(data)
            except Exception:
                pass

    def _apply_record(self, data: dict):
        """应用记录到内存统计（不重复持久化）"""
        usage = TokenUsage(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            model=data.get("model", ""),
            node_id=data.get("node_id", ""),
        )
        nid = usage.node_id
        if nid not in self._node_totals:
            self._node_totals[nid] = TokenUsage(node_id=nid)
        total = self._node_totals[nid]
        total.prompt_tokens += usage.prompt_tokens
        total.completion_tokens += usage.completion_tokens
        total.total_tokens += usage.total_tokens

    def record(self, node_id: str, prompt_tokens: int, completion_tokens: int, model: str = ""):
        """记录一次 LLM 调用"""
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
            node_id=node_id,
        )
        self._records.append(usage)

        # 更新节点汇总
        if node_id not in self._node_totals:
            self._node_totals[node_id] = TokenUsage(node_id=node_id)
        total = self._node_totals[node_id]
        total.prompt_tokens += prompt_tokens
        total.completion_tokens += completion_tokens
        total.total_tokens += prompt_tokens + completion_tokens

        # 持久化
        if self._persist_path:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(usage.to_dict(), ensure_ascii=False) + "\n")

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数（中文约 1 字 = 0.5-1 token）"""
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 0.7 + other_chars * 0.3)

    def estimate_cost(self, node_id: str, input_text: str, output_text: str = "",
                       model: str = "claude-sonnet-5") -> dict:
        """预估单次调用的成本"""
        input_tokens = self.estimate_tokens(input_text)
        output_tokens = self.estimate_tokens(output_text) if output_text else input_tokens // 2

        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-5"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return {
            "input_tokens_est": input_tokens,
            "output_tokens_est": output_tokens,
            "total_tokens_est": input_tokens + output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
            "model": model,
            "node_id": node_id,
        }

    def stats(self) -> dict:
        """获取全局统计"""
        all_records = list(self._records)
        # 也包括从磁盘加载的
        if self._node_totals:
            has_in_memory = {r.node_id for r in self._records}
            for nid, usage in self._node_totals.items():
                if nid not in has_in_memory:
                    all_records.append(usage)

        total = TokenUsage()
        for r in all_records:
            total.prompt_tokens += r.prompt_tokens
            total.completion_tokens += r.completion_tokens
            total.total_tokens += r.total_tokens

        return {
            "total_tokens": total.total_tokens,
            "total_prompt_tokens": total.prompt_tokens,
            "total_completion_tokens": total.completion_tokens,
            "estimated_cost_usd": total.estimated_cost_usd,
            "estimated_cost_cny": round(total.estimated_cost_usd * 7.2, 2),
            "total_calls": len(all_records),
            "by_node": {
                node_id: {
                    "tokens": usage.total_tokens,
                    "calls": sum(1 for r in all_records if r.node_id == node_id),
                    "cost_usd": usage.estimated_cost_usd,
                    "cost_cny": round(usage.estimated_cost_usd * 7.2, 2),
                }
                for node_id, usage in self._node_totals.items()
            },
            "project_id": self._project_id,
        }

    def print_report(self):
        """打印成本统计报告（增强版）"""
        s = self.stats()

        # 使用 Rich 表格（如果可用）
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text

            console = Console()
            console.print()
            console.print(Panel.fit(
                Text("📊 Token 消耗与成本统计", style="bold white"),
                border_style="cyan",
            ))

            # 全局概览
            overview = Table(title="全局概览", box=None)
            overview.add_column("指标", style="dim")
            overview.add_column("数值", style="bold")
            overview.add_row("总调用次数", str(s["total_calls"]))
            overview.add_row("总 Token", f"{s['total_tokens']:,}")
            overview.add_row("输入 Token", f"{s['total_prompt_tokens']:,}")
            overview.add_row("输出 Token", f"{s['total_completion_tokens']:,}")
            overview.add_row("预估成本 (USD)", f"${s['estimated_cost_usd']:.4f}")
            overview.add_row("预估成本 (CNY)", f"¥{s['estimated_cost_cny']:.2f}")
            console.print(overview)

            # 按节点明细
            if s["by_node"]:
                detail = Table(title="节点明细", box=None)
                detail.add_column("节点", style="cyan")
                detail.add_column("Tokens", justify="right")
                detail.add_column("调用次数", justify="right")
                detail.add_column("成本 USD", justify="right")
                detail.add_column("成本 CNY", justify="right")
                detail.add_column("占比", justify="right")

                for node_id, info in sorted(s["by_node"].items()):
                    pct = (info["tokens"] / max(s["total_tokens"], 1)) * 100
                    detail.add_row(
                        node_id,
                        f"{info['tokens']:,}",
                        str(info["calls"]),
                        f"${info['cost_usd']:.4f}",
                        f"¥{info['cost_cny']:.2f}",
                        f"{pct:.1f}%",
                    )
                console.print(detail)

                # 成本建议
                if s["estimated_cost_usd"] > 1:
                    console.print()
                    console.print("[yellow]💡 成本优化建议:[/yellow]")
                    console.print("  • 对频繁调用的节点使用 haiku 模型降本")
                    console.print("  • 启用 Prompt Caching 减少重复输入成本")
                    console.print("  • 合并小 Prompt 请求，减少 round-trip")

            console.print()

        except ImportError:
            # 纯文本降级（Rich 必定可用，此分支保底）
            print("\n" + "=" * 60)
            print("📊 Token 消耗与成本统计")
            print("=" * 60)
            print(f"  总调用次数: {s['total_calls']}")
            print(f"  总 Token:    {s['total_tokens']:>10,}")
            print(f"  输入 Token:  {s['total_prompt_tokens']:>10,}")
            print(f"  输出 Token:  {s['total_completion_tokens']:>10,}")
            print(f"  预估成本:    ${s['estimated_cost_usd']:.4f} (¥{s['estimated_cost_cny']:.2f})")
            print("-" * 60)
            for node_id, info in sorted(s["by_node"].items()):
                print(f"  {node_id}: {info['tokens']:>8,} tokens, {info['calls']} calls, "
                      f"${info['cost_usd']:.4f}")
            print("=" * 60 + "\n")


# 全局实例
token_counter = TokenCounter()

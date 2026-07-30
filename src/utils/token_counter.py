"""Token 消耗统计

追踪每次 LLM 调用的 Token 消耗，支持按节点汇总统计。
"""

from dataclasses import dataclass, field
from datetime import datetime


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


class TokenCounter:
    """全局 Token 计数器"""

    def __init__(self):
        self._records: list[TokenUsage] = []
        self._node_totals: dict[str, TokenUsage] = {}

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

    def stats(self) -> dict:
        """获取全局统计"""
        total = TokenUsage()
        for r in self._records:
            total.prompt_tokens += r.prompt_tokens
            total.completion_tokens += r.completion_tokens
            total.total_tokens += r.total_tokens

        return {
            "total_tokens": total.total_tokens,
            "total_prompt_tokens": total.prompt_tokens,
            "total_completion_tokens": total.completion_tokens,
            "estimated_cost_usd": total.estimated_cost_usd,
            "total_calls": len(self._records),
            "by_node": {
                node_id: {
                    "tokens": usage.total_tokens,
                    "calls": sum(1 for r in self._records if r.node_id == node_id),
                    "cost_usd": usage.estimated_cost_usd,
                }
                for node_id, usage in self._node_totals.items()
            },
        }

    def print_report(self):
        """打印成本统计报告"""
        s = self.stats()
        print("\n" + "=" * 60)
        print("📊 Token 消耗统计")
        print("=" * 60)
        print(f"  总调用次数: {s['total_calls']}")
        print(f"  总 Token:    {s['total_tokens']:>10,}")
        print(f"  输入 Token:  {s['total_prompt_tokens']:>10,}")
        print(f"  输出 Token:  {s['total_completion_tokens']:>10,}")
        print(f"  预估成本:    ${s['estimated_cost_usd']:.4f}")
        print("-" * 60)
        for node_id, info in sorted(s["by_node"].items()):
            print(f"  {node_id}: {info['tokens']:>8,} tokens, {info['calls']} calls, ${info['cost_usd']:.4f}")
        print("=" * 60 + "\n")


# 全局实例
token_counter = TokenCounter()

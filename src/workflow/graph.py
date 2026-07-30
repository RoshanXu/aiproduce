"""完整 LangGraph 工作流图定义

21节点完整工作流，支持：
- Thin Slice 模式（8节点精简链路）
- 完整模式（21节点全流程）
"""

from typing import Literal
from src.workflow.state import WorkflowState, NodeStatus


# ─── 节点函数注册表 ───────────────────────────────

NODE_REGISTRY: dict[str, dict] = {
    "N01": {"name": "项目初始化", "agent": "scheduler", "phase": 1},
    "N02": {"name": "原著文本拆分与分层摘要", "agent": "deconstructor", "phase": 1},
    "N03": {"name": "首轮资产库构建", "agent": "character_asset+world_asset+timeline_asset", "phase": 1},
    "N04": {"name": "改编策划总纲生成", "agent": "adaptation_planner", "phase": 2},
    "N05": {"name": "策划案合规校验", "agent": "compliance_checker", "phase": 2},
    "N06": {"name": "资产库迭代更新", "agent": "character_asset+world_asset+timeline_asset", "phase": 2},
    "N07": {"name": "全剧分集大纲生成", "agent": "episode_outliner", "phase": 2},
    "N08": {"name": "大纲全局校验", "agent": "character_checker+timeline_checker", "phase": 2},
    "N09": {"name": "单集场次拆分", "agent": "scene_splitter", "phase": 3},
    "N10": {"name": "场次清单校验", "agent": "format_checker", "phase": 3},
    "N11": {"name": "单场剧本生成", "agent": "scene_writer", "phase": 4},
    "N12": {"name": "人设一致性校验", "agent": "character_checker", "phase": 4},
    "N13": {"name": "时间线与细节校验", "agent": "timeline_checker", "phase": 4},
    "N14": {"name": "格式与合规校验", "agent": "format_checker", "phase": 4},
    "N15": {"name": "剧本入库", "agent": "scheduler", "phase": 4},
    "N16": {"name": "单集剧本拼接", "agent": "scheduler", "phase": 5},
    "N17": {"name": "单集节奏优化", "agent": "final_polisher", "phase": 5},
    "N18": {"name": "全剧拼接与全局审计", "agent": "compliance_checker", "phase": 5},
    "N19": {"name": "全剧统稿打磨", "agent": "final_polisher", "phase": 5},
    "N20": {"name": "终稿合规终审", "agent": "compliance_checker", "phase": 5},
    "N21": {"name": "项目结项归档", "agent": "scheduler", "phase": 5},
}

# Thin Slice 模式节点列表
THIN_SLICE_NODES = ["N01", "N02", "N03", "N04", "N07", "N09", "N11", "N12"]


def get_phase_nodes(phase: int) -> list[str]:
    """获取指定阶段的节点列表"""
    return [nid for nid, info in NODE_REGISTRY.items() if info["phase"] == phase]


def get_next_node(current_node: str, thin_slice: bool = False) -> str | None:
    """获取工作流中的下一个节点"""
    node_list = THIN_SLICE_NODES if thin_slice else list(NODE_REGISTRY.keys())
    try:
        idx = node_list.index(current_node)
        return node_list[idx + 1] if idx + 1 < len(node_list) else None
    except (ValueError, IndexError):
        return None


def build_workflow_graph(thin_slice: bool = True):
    """构建 LangGraph 工作流图

    Args:
        thin_slice: True=精简验证链路, False=完整21节点

    Returns:
        LangGraph StateGraph（函数实现留待阶段1-4）
    """
    # 阶段1-4 将在此实现完整的 LangGraph StateGraph
    # 包含所有节点的 add_node/add_edge/add_conditional_edges
    pass

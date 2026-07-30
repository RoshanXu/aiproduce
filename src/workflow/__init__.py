"""工作流包"""

from src.workflow.state import WorkflowState, NodeStatus
from src.workflow.edges import (
    check_n02_pass, check_n03_pass, check_n12_pass, check_node_pass,
)
from src.workflow.graph import (
    NODE_REGISTRY, THIN_SLICE_NODES,
    get_phase_nodes, get_next_node, build_workflow_graph,
)

__all__ = [
    "WorkflowState", "NodeStatus",
    "check_n02_pass", "check_n03_pass", "check_n12_pass", "check_node_pass",
    "NODE_REGISTRY", "THIN_SLICE_NODES",
    "get_phase_nodes", "get_next_node", "build_workflow_graph",
]

"""LangGraph 工作流共享状态"""

from typing import Optional, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class WorkflowState:
    """LangGraph 工作流全局状态

    承载全流程共享数据，每个节点执行前后读写此状态。
    """
    # 项目配置（初始化后不变）
    project_config: Optional[dict] = field(default=None)

    # 资产库（随 N03/N06 更新）
    asset_library: Optional[dict] = field(default=None)  # AssetLibrary as dict
    asset_version: str = field(default="1.0")

    # 工作层产出物
    work_layer: dict = field(default_factory=dict)  # {node_id: output_data}

    # 校验报告累积
    validation_reports: list[dict] = field(default_factory=list)

    # 节点状态追踪
    node_statuses: dict[str, NodeStatus] = field(default_factory=dict)

    # 当前执行上下文
    current_node: str = field(default="")
    current_episode_id: str = field(default="")
    current_scene_id: str = field(default="")

    # 错误处理
    errors: list[dict] = field(default_factory=list)  # [{node_id, error, timestamp}]
    retry_counts: dict[str, int] = field(default_factory=dict)

    # 时间戳
    started_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)

    def set_node_status(self, node_id: str, status: NodeStatus):
        self.node_statuses[node_id] = status
        self.updated_at = datetime.now()

    def get_node_output(self, node_id: str) -> Optional[dict]:
        return self.work_layer.get(node_id)

    def set_node_output(self, node_id: str, output: dict):
        self.work_layer[node_id] = output
        self.updated_at = datetime.now()

    def add_validation_report(self, report: dict):
        self.validation_reports.append(report)

    def add_error(self, node_id: str, error: str):
        self.errors.append({
            "node_id": node_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

    def can_retry(self, node_id: str, max_retries: int = 3) -> bool:
        count = self.retry_counts.get(node_id, 0)
        return count < max_retries

    def increment_retry(self, node_id: str):
        self.retry_counts[node_id] = self.retry_counts.get(node_id, 0) + 1

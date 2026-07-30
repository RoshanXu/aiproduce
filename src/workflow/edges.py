"""准入准出条件路由

每个节点的条件路由逻辑。
"""

from src.workflow.state import WorkflowState, NodeStatus


def check_n02_pass(state: WorkflowState) -> bool:
    """N02 准出校验：语义块拆分质量"""
    output = state.work_layer.get("N02", {})
    chunks = output.get("chunks", [])
    if not chunks:
        return False

    # 检查拆分点是否在语义边界
    hard_cuts = [c for c in chunks if c.get("boundary_type") == "word_count_only"]
    if hard_cuts:
        return False

    # 检查摘要覆盖面
    chapters_covered = set(c.get("chapter", "") for c in chunks)
    if not chapters_covered:
        return False

    return True


def check_n03_pass(state: WorkflowState) -> bool:
    """N03 准出校验：资产库完整性"""
    output = state.work_layer.get("N03", {})
    asset_lib = output.get("asset_library", {})

    characters = asset_lib.get("characters", [])
    if not characters:
        return False

    # 核心人物（TOP10）字段完整度≥90%
    required_fields = ["name", "core_identity", "core_personality", "key_experiences", "core_goal", "relationships"]
    for char in characters[:10]:
        filled = sum(1 for f in required_fields if char.get(f))
        if filled / len(required_fields) < 0.9:
            return False

    return True


def check_n12_pass(state: WorkflowState) -> bool:
    """N12 准出校验：人设一致性"""
    report = state.work_layer.get("N12", {})

    # 阻塞级偏差必须为0
    blocking_issues = report.get("blocking_issues", [])
    if blocking_issues:
        return False

    # 警告级偏差按人物统计≤2条/人
    warning_issues = report.get("warning_issues", [])
    per_char_warnings: dict[str, int] = {}
    for issue in warning_issues:
        char_id = issue.get("char_id", "unknown")
        per_char_warnings[char_id] = per_char_warnings.get(char_id, 0) + 1
    if any(count > 2 for count in per_char_warnings.values()):
        return False

    return True


def check_node_pass(state: WorkflowState, node_id: str, max_retries: int = 3) -> bool:
    """通用节点准出判断

    综合检查：输出存在 + retry未超限
    """
    output = state.work_layer.get(node_id)
    if output is None:
        return False

    if not state.can_retry(node_id, max_retries):
        state.set_node_status(node_id, NodeStatus.FAILED)
        return False

    return True

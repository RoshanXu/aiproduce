"""统一日志系统

结构化日志 + 节点级追踪。
"""

import logging
import time
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager


class NodeLogger:
    """节点级日志追踪器"""

    def __init__(self, log_dir: str | Path = "workspace/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("aiproduce")
        self._logger.setLevel(logging.DEBUG)

        # 文件 handler
        fh = logging.FileHandler(
            self.log_dir / f"aiproduce_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        self._logger.addHandler(fh)

    @contextmanager
    def node_context(self, node_id: str, node_name: str):
        """节点运行上下文管理器

        自动记录节点开始/结束/耗时/异常。
        """
        logger = logging.getLogger(f"aiproduce.{node_id}")
        logger.info(f"[{node_name}] 开始执行")
        start = time.time()
        try:
            yield logger
            elapsed = time.time() - start
            logger.info(f"[{node_name}] 执行完成 ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[{node_name}] 执行失败 ({elapsed:.1f}s): {e}")
            raise

    def info(self, msg: str):
        self._logger.info(msg)

    def warn(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)


# 全局实例
node_logger = NodeLogger()

"""Worker Cluster Autoscaling Governance & Capacity Metrics Service (Non-invasive hooks)."""

from datetime import datetime, timezone
from typing import Any, List

from app.core.logging import get_logger
from app.domain.entities.scan_schedule import WorkerAutoscaleMetrics

logger = get_logger("vulnova.worker_autoscaler")


class WorkerAutoscalerService:
    """Isolated, non-invasive worker cluster capacity monitor computing scaling metrics recommendations."""

    def __init__(
        self, min_workers: int = 1, max_workers: int = 10, queue_threshold: int = 5
    ) -> None:
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.queue_threshold = queue_threshold

    def calculate_cluster_metrics(
        self, active_worker_nodes: List[Any], pending_queue_depth: int = 0
    ) -> WorkerAutoscaleMetrics:
        """Compute cluster capacity metrics and recommend scaling signals without modifying infrastructure."""
        active_count = len(active_worker_nodes)
        idle_count = sum(
            1
            for node in active_worker_nodes
            if getattr(node, "current_workload", 0) == 0
        )

        recommended = active_count
        action = "STABLE"

        if (
            pending_queue_depth >= self.queue_threshold
            and active_count < self.max_workers
        ):
            recommended = min(self.max_workers, active_count + 1)
            action = "SCALE_UP"
        elif (
            pending_queue_depth == 0
            and idle_count > 1
            and active_count > self.min_workers
        ):
            recommended = max(self.min_workers, active_count - 1)
            action = "SCALE_DOWN"

        metrics = WorkerAutoscaleMetrics(
            active_workers_count=active_count,
            idle_workers_count=idle_count,
            pending_queue_depth=pending_queue_depth,
            recommended_workers_count=recommended,
            scaling_action_suggested=action,
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(
            "worker_autoscale.metrics_computed",
            active=active_count,
            pending=pending_queue_depth,
            action=action,
            recommended=recommended,
        )

        return metrics

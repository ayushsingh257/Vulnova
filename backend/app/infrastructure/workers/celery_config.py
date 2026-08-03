"""Celery Configuration Settings for Distributed Worker Sandbox Cluster."""

import os
from typing import Any, Dict

# Redis Broker and Result Backend Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
    broker_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

result_backend = broker_url

# Task Serialization & Security Settings
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Task Execution & Reliability Controls
task_ack_late = True
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1
worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", 4))
task_time_limit = 3600  # Hard time limit: 1 hour
task_soft_time_limit = 3300  # Soft time limit: 55 minutes

# Task Queue Definitions & Priority Routing
task_queues = {
    "scans.high": {
        "exchange": "scans.high",
        "routing_key": "scans.high",
    },
    "scans.default": {
        "exchange": "scans.default",
        "routing_key": "scans.default",
    },
    "scans.low": {
        "exchange": "scans.low",
        "routing_key": "scans.low",
    },
    "ai.priority": {
        "exchange": "ai.priority",
        "routing_key": "ai.priority",
    },
}

task_default_queue = "scans.default"

task_routes: Dict[str, Any] = {
    "app.infrastructure.workers.tasks.execute_scan_job_task": {
        "queue": "scans.default"
    },
    "app.infrastructure.workers.tasks.cancel_scan_job_task": {"queue": "scans.high"},
    "app.infrastructure.workers.tasks.cleanup_scan_artifacts_task": {
        "queue": "scans.low"
    },
}

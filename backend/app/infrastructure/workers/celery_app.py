"""Celery Application Factory & Worker Signal Handlers."""

from typing import Any

from celery import Celery
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutdown,
)

from app.core.logging import get_logger
from app.infrastructure.workers import celery_config

logger = get_logger(__name__)

# Initialize Celery Application
celery_app = Celery("vulnova_workers")
celery_app.config_from_object(celery_config)

# Auto-discover tasks in worker package
celery_app.autodiscover_tasks(["app.infrastructure.workers"])


@worker_ready.connect  # type: ignore[untyped-decorator]
def on_worker_ready(sender: Any, **kwargs: Any) -> None:
    """Signal handler executed when Celery worker process initializes successfully."""
    consumer = getattr(sender, "task_consumer", None)
    queues = getattr(consumer, "queues", []) if consumer else []
    queue_names = [getattr(q, "name", str(q)) for q in queues]

    logger.info(
        "celery_worker.ready",
        worker_hostname=getattr(sender, "hostname", "unknown"),
        queues=queue_names,
    )


@worker_shutdown.connect  # type: ignore[untyped-decorator]
def on_worker_shutdown(sender: Any, **kwargs: Any) -> None:
    """Signal handler executed when Celery worker process initiates graceful shutdown."""
    logger.info(
        "celery_worker.shutdown",
        worker_hostname=getattr(sender, "hostname", "unknown"),
    )


@task_prerun.connect  # type: ignore[untyped-decorator]
def on_task_prerun(
    task_id: str, task: Any, args: Any, kwargs: Any, **extra: Any
) -> None:
    """Signal handler executed immediately before task execution."""
    logger.info(
        "celery_task.prerun",
        task_id=task_id,
        task_name=getattr(task, "name", str(task)),
    )


@task_postrun.connect  # type: ignore[untyped-decorator]
def on_task_postrun(
    task_id: str, task: Any, retval: Any, state: str, **extra: Any
) -> None:
    """Signal handler executed immediately after task execution finishes."""
    logger.info(
        "celery_task.postrun",
        task_id=task_id,
        task_name=getattr(task, "name", str(task)),
        state=state,
    )


@task_failure.connect  # type: ignore[untyped-decorator]
def on_task_failure(
    task_id: str,
    exception: Exception,
    args: Any,
    kwargs: Any,
    traceback: Any,
    **extra: Any,
) -> None:
    """Signal handler executed on unhandled task failures."""
    logger.error(
        "celery_task.failure",
        task_id=task_id,
        error=str(exception),
    )

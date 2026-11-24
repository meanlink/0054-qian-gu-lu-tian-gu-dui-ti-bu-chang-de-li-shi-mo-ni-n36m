"""Backward-compatible entry point for weather corrections.

New code should use correction_batch.submit.  The aliases preserve the small
service-function surface used by scripts and tests.
"""
from correction_batch import (
    Block,
    get_batch,
    list_batches,
    retry_batch,
    submit,
)

__all__ = [
    "Block", "add", "queue", "queue_correction", "create_batch",
    "retry_batch", "get_batch", "list_batches",
]


def add(cx, data, actor="operator", idempotency_key=None):
    return submit(cx, data, actor=actor, idempotency_key=idempotency_key)


queue = add
queue_correction = add
create_batch = add

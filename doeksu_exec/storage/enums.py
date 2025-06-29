from enum import Enum


class WorkflowRunStatus(Enum):
    """Status of a workflow run."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
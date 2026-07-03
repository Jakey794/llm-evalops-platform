from enum import StrEnum


class ModelProvider(StrEnum):
    OPENAI = "openai"


class EvalRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

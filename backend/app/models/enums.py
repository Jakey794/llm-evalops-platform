from enum import StrEnum


class ModelProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"


class EvalRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

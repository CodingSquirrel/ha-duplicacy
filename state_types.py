from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Literal, Any

@dataclass
class ProgressState:
    progress: int
    time_remaining: timedelta
    time_elapsed: timedelta
    upload_speed: int
    running: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'time_remaining': str(self.time_remaining),
            'time_elapsed': str(self.time_elapsed)
        }

@dataclass
class CompletionState:
    revision: int = 0
    time_started: datetime = datetime.fromtimestamp(0)
    time_finished: datetime = datetime.fromtimestamp(0)
    time_elapsed: timedelta = timedelta()
    files: int = 0
    files_size: int = 0
    new_files: int = 0
    new_files_size: int = 0
    chunks: int = 0
    chunks_size: int = 0
    new_chunks: int = 0
    new_chunks_size: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def state(self) -> str:
        if self.errors:
            return 'error'
        if self.warnings:
            return 'warning'
        return 'success'

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'time_started': str(self.time_started),
            'time_finished': str(self.time_finished),
            'time_elapsed': str(self.time_elapsed),
            'state': self.state
        }

"""
Progress Tracking System.
Tracks execution progress with step status, ETA, and real-time updates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from datetime import datetime, timedelta
import time


class ProgressStatus(Enum):
    """Status of a step or overall execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


@dataclass
class ProgressStep:
    """Progress information for a single step."""
    step_id: str
    name: str
    status: ProgressStatus = ProgressStatus.PENDING
    progress_percent: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_remaining_ms: Optional[float] = None
    message: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ProgressTracker:
    """Tracks overall execution progress."""
    total_steps: int
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    steps: list[ProgressStep] = field(default_factory=list)
    current_step_index: int = 0
    on_progress_update: Optional[Callable] = None  # Callback for progress updates
    on_step_complete: Optional[Callable] = None   # Callback for step completion

    def __post_init__(self):
        """Initialize step tracking."""
        self.step_start_times: dict[str, datetime] = {}
        self.step_durations: dict[str, float] = {}  # Historical durations for ETA

    def add_step(self, step_id: str, name: str) -> None:
        """Add a step to track."""
        progress_step = ProgressStep(step_id=step_id, name=name)
        self.steps.append(progress_step)

    def start_step(self, step_id: str) -> None:
        """Mark a step as started."""
        self.step_start_times[step_id] = datetime.now()

        for step in self.steps:
            if step.step_id == step_id:
                step.status = ProgressStatus.RUNNING
                step.started_at = datetime.now()
                break

        # Update current step index
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                self.current_step_index = i
                break

        self._notify_progress()

    def update_step_progress(self, step_id: str, progress_percent: float, message: str = "") -> None:
        """Update progress for a running step."""
        for step in self.steps:
            if step.step_id == step_id:
                step.progress_percent = min(progress_percent, 100.0)
                if message:
                    step.message = message
                break

        self._notify_progress()

    def complete_step(self, step_id: str, success: bool = True) -> None:
        """Mark a step as completed."""
        completed_at = datetime.now()

        for step in self.steps:
            if step.step_id == step_id:
                step.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
                step.completed_at = completed_at
                step.progress_percent = 100.0 if success else step.progress_percent

                # Record duration for future ETA estimation
                if step_id in self.step_start_times:
                    duration = (completed_at - self.step_start_times[step_id]).total_seconds() * 1000
                    self.step_durations[step_id] = duration

                break

        if self.on_step_complete:
            self.on_step_complete(step_id, success)

        self._notify_progress()

    def skip_step(self, step_id: str, reason: str = "") -> None:
        """Mark a step as skipped."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = ProgressStatus.SKIPPED
                step.message = reason or "Skipped"
                break

        self._notify_progress()

    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = ProgressStatus.FAILED
                step.message = error
                break

        self._notify_progress()

    @property
    def overall_progress(self) -> float:
        """Calculate overall progress percentage."""
        if not self.steps:
            return 0.0

        total = sum(step.progress_percent for step in self.steps)
        return total / len(self.steps)

    @property
    def completed_steps_count(self) -> int:
        """Count of completed steps."""
        return sum(1 for step in self.steps if step.status == ProgressStatus.COMPLETED)

    @property
    def failed_steps_count(self) -> int:
        """Count of failed steps."""
        return sum(1 for step in self.steps if step.status == ProgressStatus.FAILED)

    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """Estimate remaining time based on historical data."""
        if not self.steps:
            return None

        remaining_ms = 0.0

        for step in self.steps:
            if step.status == ProgressStatus.PENDING or step.status == ProgressStatus.WAITING:
                # Use historical average for pending steps
                if step.step_id in self.step_durations:
                    remaining_ms += self.step_durations[step.step_id]
                else:
                    # Use average of known durations
                    if self.step_durations:
                        avg_duration = sum(self.step_durations.values()) / len(self.step_durations)
                        remaining_ms += avg_duration

            elif step.status == ProgressStatus.RUNNING:
                # Estimate based on current progress
                if step.progress_percent > 0:
                    elapsed_ms = (datetime.now() - step.started_at).total_seconds() * 1000
                    estimated_total = elapsed_ms / (step.progress_percent / 100)
                    remaining_ms += estimated_total - elapsed_ms
                else:
                    if self.step_durations:
                        avg_duration = sum(self.step_durations.values()) / len(self.step_durations)
                        remaining_ms += avg_duration

        if remaining_ms > 0:
            return timedelta(milliseconds=remaining_ms)
        return None

    def _notify_progress(self) -> None:
        """Trigger progress callback if set."""
        if self.on_progress_update:
            self.on_progress_update(self.get_summary())

    def get_summary(self) -> dict:
        """Get progress summary as dictionary."""
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps_count,
            "failed_steps": self.failed_steps_count,
            "current_step_index": self.current_step_index,
            "current_step": self.steps[self.current_step_index].step_id if self.steps else None,
            "overall_progress": self.overall_progress,
            "estimated_remaining": str(self.estimated_remaining_time) if self.estimated_remaining_time else None,
            "elapsed_time": str(datetime.now() - self.start_time),
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "status": s.status.value,
                    "progress": s.progress_percent,
                    "message": s.message
                }
                for s in self.steps
            ]
        }

    def format_progress_bar(self, width: int = 50) -> str:
        """Format progress as ASCII progress bar."""
        filled = int(self.overall_progress * width / 100)
        bar = "=" * filled + "-" * (width - filled)
        return f"[{bar}] {self.overall_progress:.1f}%"


def format_progress_display(tracker: ProgressTracker) -> str:
    """Format progress tracker state as human-readable display."""
    lines = []
    lines.append("Execution Progress:")
    lines.append(f"  {tracker.format_progress_bar()}")
    lines.append(f"  {tracker.completed_steps_count}/{tracker.total_steps} steps completed")

    eta = tracker.estimated_remaining_time
    if eta:
        lines.append(f"  ETA: {eta}")

    lines.append("")

    # Show recent/current steps
    for step in tracker.steps:
        status_icon = {
            ProgressStatus.PENDING: "[ ]",
            ProgressStatus.RUNNING: "[>]",
            ProgressStatus.COMPLETED: "[X]",
            ProgressStatus.FAILED: "[!]",
            ProgressStatus.SKIPPED: "[-]",
            ProgressStatus.WAITING: "[w]"
        }.get(step.status, "[?]")

        if step.status == ProgressStatus.RUNNING:
            lines.append(f"  {status_icon} {step.name} - {step.progress_percent:.0f}% {step.message}")
        elif step.status != ProgressStatus.PENDING:
            lines.append(f"  {status_icon} {step.name} {step.message}")

    return "\n".join(lines)

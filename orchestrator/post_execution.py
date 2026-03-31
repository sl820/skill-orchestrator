"""
Post-Execution Processing.
Handles cleanup, notification, and result summarization after execution.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable
from .models import ExecutionResult, ExecutionPlan, StepResult


@dataclass
class PostExecutionConfig:
    """Configuration for post-execution processing."""
    cleanup_on_success: bool = True
    cleanup_on_failure: bool = False
    notify_on_complete: bool = True
    store_results: bool = True
    on_success_callback: Optional[Callable] = None
    on_failure_callback: Optional[Callable] = None


class PostExecutionHandler:
    """
    Handles post-execution tasks.

    Tasks include:
    - Cleanup temporary files
    - Sending notifications
    - Storing execution history
    - Triggering callbacks
    """

    def __init__(self, config: PostExecutionConfig | None = None):
        """
        Initialize post-execution handler.

        Args:
            config: Optional configuration
        """
        self.config = config or PostExecutionConfig()
        self.execution_history: list[ExecutionResult] = []

    def process(self, result: ExecutionResult, plan: ExecutionPlan) -> None:
        """
        Process execution result.

        Args:
            result: Execution result to process
            plan: Original execution plan
        """
        # Store result
        if self.config.store_results:
            self._store_result(result)

        # Cleanup based on outcome
        if result.success and self.config.cleanup_on_success:
            self._cleanup(result, plan)
        elif not result.success and self.config.cleanup_on_failure:
            self._cleanup(result, plan)

        # Trigger callbacks
        if result.success and self.config.on_success_callback:
            self.config.on_success_callback(result, plan)
        elif not result.success and self.config.on_failure_callback:
            self.config.on_failure_callback(result, plan)

        # Send notifications
        if self.config.notify_on_complete:
            self._send_notification(result)

    def _store_result(self, result: ExecutionResult) -> None:
        """Store execution result in history."""
        self.execution_history.append(result)

    def _cleanup(self, result: ExecutionResult, plan: ExecutionPlan) -> None:
        """Clean up temporary resources."""
        # Identify temporary files from step outputs
        temp_files = []
        for step_result in result.step_results:
            if step_result.output and isinstance(step_result.output, dict):
                # Look for temp file markers
                for key, value in step_result.output.items():
                    if key.startswith("_temp_") or key.endswith("_cleanup"):
                        temp_files.append(value)

        # In a real implementation, would delete these files
        # For now, just log
        pass

    def _send_notification(self, result: ExecutionResult) -> None:
        """Send execution completion notification."""
        status = "SUCCESS" if result.success else "FAILED"
        summary = self._generate_summary(result)

        # In a real implementation, would send notification
        # (e.g., Slack message, email, etc.)
        print(f"[Notification] Execution {status}: {summary}")

    def _generate_summary(self, result: ExecutionResult) -> str:
        """Generate execution summary string."""
        completed = result.completed_steps
        failed = result.failed_steps
        duration = result.total_duration_ms / 1000 if result.total_duration_ms else 0

        return f"{completed} completed, {failed} failed, {duration:.1f}s"

    def get_history(self, limit: Optional[int] = None) -> list[ExecutionResult]:
        """
        Get execution history.

        Args:
            limit: Optional limit on number of results to return

        Returns:
            List of historical execution results
        """
        if limit:
            return self.execution_history[-limit:]
        return self.execution_history

    def get_statistics(self) -> dict:
        """Get execution statistics."""
        total = len(self.execution_history)
        if total == 0:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0
            }

        successes = sum(1 for r in self.execution_history if r.success)
        total_duration = sum(
            r.total_duration_ms for r in self.execution_history
            if r.total_duration_ms
        )

        return {
            "total_executions": total,
            "success_rate": successes / total,
            "avg_duration_ms": total_duration / total if total else 0.0,
            "total_errors": sum(len(r.errors) for r in self.execution_history)
        }


def format_execution_summary(result: ExecutionResult) -> str:
    """Format execution result as a concise summary."""
    status = "SUCCESS" if result.success else "FAILED"

    lines = []
    lines.append(f"Execution: {status}")
    lines.append(f"Steps: {result.completed_steps}/{len(result.step_results)} completed")

    if result.total_duration_ms:
        lines.append(f"Duration: {result.total_duration_ms / 1000:.2f}s")

    if result.errors:
        lines.append(f"Errors: {len(result.errors)}")
        for error in result.errors[:3]:  # Show first 3 errors
            lines.append(f"  - {error}")

    return " | ".join(lines)

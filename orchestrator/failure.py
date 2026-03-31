"""
Failure Handling System.
Handles different failure modes and rollback strategies.
"""

from __future__ import annotations
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from .models import FailureMode, StepResult, ExecutionStep, ExecutionPlan


class RollbackAction(Enum):
    """Types of rollback actions."""
    DELETE_FILE = "DELETE_FILE"
    RESTORE_FILE = "RESTORE_FILE"
    REVERT_CONFIG = "REVERT_CONFIG"
    CALLBACK = "CALLBACK"
    COMPENSATE = "COMPENSATE"
    NOTIFY = "NOTIFY"


@dataclass
class RollbackSpec:
    """Specification for a rollback action."""
    action: RollbackAction
    target: str                    # File path, config key, etc.
    backup: Optional[str] = None   # Backup location if applicable
    callback: Optional[Callable] = None  # Custom rollback function


@dataclass
class FailureContext:
    """Context passed to failure handlers."""
    failed_step: ExecutionStep
    error: Exception
    plan: ExecutionPlan
    completed_steps: list[StepResult]
    partial_results: dict
    can_rollback: bool = True
    rollback_actions: list[RollbackSpec] = field(default_factory=list)


@dataclass
class FailureResult:
    """Result of failure handling."""
    handled: bool = False
    rolled_back: bool = False
    recovered: bool = False
    message: str = ""
    actions_taken: list[str] = field(default_factory=list)
    fallback_output: Optional[dict] = None


def create_rollback_spec(
    step: ExecutionStep,
    rollback_on: Optional[str] = None
) -> list[RollbackSpec]:
    """
    Create rollback specifications for a step based on its outputs.

    Args:
        step: The execution step
        rollback_on: Step ID to rollback on failure

    Returns:
        List of rollback specifications
    """
    specs = []

    # Check step outputs for files that need cleanup
    for output_key, output_value in step.outputs.items():
        if isinstance(output_value, str) and output_value.startswith("/"):
            # File path output
            specs.append(RollbackSpec(
                action=RollbackAction.DELETE_FILE,
                target=output_value
            ))

    # Add explicit rollback actions from step definition
    if step.rollback_on:
        # Could parse rollback instructions from step.rollback_on
        pass

    return specs


def handle_failure(
    context: FailureContext,
    mode: FailureMode = FailureMode.FAIL_SOFT
) -> FailureResult:
    """
    Handle a step failure based on the failure mode.

    Args:
        context: Failure context
        mode: Failure handling mode

    Returns:
        FailureResult describing what happened
    """
    result = FailureResult(handled=True)

    if mode == FailureMode.FAIL_FAST:
        return _handle_fail_fast(context)

    elif mode == FailureMode.FAIL_SOFT:
        return _handle_fail_soft(context)

    elif mode == FailureMode.CONTINUE:
        return _handle_continue(context)

    return result


def _handle_fail_fast(context: FailureContext) -> FailureResult:
    """Fail fast: rollback and stop execution."""
    result = FailureResult(handled=True)

    # Attempt rollback
    if context.can_rollback and context.rollback_actions:
        result.rolled_back = _execute_rollback(context.rollback_actions)
        result.actions_taken.append("rollback_executed" if result.rolled_back else "rollback_failed")

    result.message = "FAIL_FAST: Stopping execution due to failure"
    result.actions_taken.append("execution_stopped")

    return result


def _handle_fail_soft(context: FailureContext) -> FailureResult:
    """Fail soft: try alternatives, skip if none available."""
    result = FailureResult(handled=True)

    # Check if step has fallback
    if context.failed_step.fallback_used:
        result.message = "FAIL_SOFT: Fallback already attempted"
        return result

    # Check for alternative approaches
    # This would integrate with the planning system to find alternatives
    has_alternatives = False

    if has_alternatives:
        result.recovered = True
        result.message = "FAIL_SOFT: Alternative path available"
        result.actions_taken.append("alternative_selected")
    else:
        result.message = "FAIL_SOFT: No alternatives, skipping step"
        result.actions_taken.append("step_skipped")

    return result


def _handle_continue(context: FailureContext) -> FailureResult:
    """Continue: execute all steps, report at end."""
    result = FailureResult(handled=True)
    result.message = "CONTINUE: Recording failure, continuing execution"
    result.actions_taken.append("failure_recorded")

    return result


def _execute_rollback(actions: list[RollbackSpec]) -> bool:
    """
    Execute rollback actions.

    Args:
        actions: List of rollback specifications

    Returns:
        True if all rollbacks succeeded
    """
    success = True

    for spec in actions:
        try:
            if spec.action == RollbackAction.DELETE_FILE:
                if os.path.exists(spec.target):
                    os.remove(spec.target)

            elif spec.action == RollbackAction.RESTORE_FILE:
                if spec.backup and os.path.exists(spec.backup):
                    shutil.copy2(spec.backup, spec.target)

            elif spec.action == RollbackAction.CALLBACK:
                if spec.callback:
                    spec.callback()

        except Exception:
            success = False

    return success


def analyze_failure(
    step: ExecutionStep,
    error: Exception,
    historical_failures: dict | None = None
) -> dict:
    """
    Analyze a failure to provide insights.

    Args:
        step: The step that failed
        error: The exception that occurred
        historical_failures: Optional historical failure data

    Returns:
        Dictionary with failure analysis
    """
    analysis = {
        "step_id": step.step_id,
        "skill": step.skill,
        "action": step.action,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "likely_cause": _infer_likely_cause(error),
        "suggested_fix": _suggest_fix(error, step),
        "recurrence_count": 0,
        "is_known_issue": False
    }

    # Check historical failures
    if historical_failures:
        key = f"{step.skill}:{step.action}"
        if key in historical_failures:
            analysis["recurrence_count"] = historical_failures[key].get("count", 0)
            analysis["is_known_issue"] = analysis["recurrence_count"] > 2

    return analysis


def _infer_likely_cause(error: Exception) -> str:
    """Infer likely cause from error type."""
    error_msg = str(error).lower()

    if "timeout" in error_msg or "timed out" in error_msg:
        return "Timeout - target may be slow or unresponsive"
    elif "not found" in error_msg or "does not exist" in error_msg:
        return "Resource not found - check paths and URLs"
    elif "permission" in error_msg or "denied" in error_msg:
        return "Permission error - check access rights"
    elif "memory" in error_msg or "out of memory" in error_msg:
        return "Memory issue - consider reducing data size"
    elif "connection" in error_msg or "network" in error_msg:
        return "Network issue - check connectivity"
    elif "invalid" in error_msg or "malformed" in error_msg:
        return "Invalid input - check data format"
    else:
        return "Unknown error - see details"


def _suggest_fix(error: Exception, step: ExecutionStep) -> str:
    """Suggest a fix based on error and step."""
    cause = _infer_likely_cause(error)

    if "timeout" in cause.lower():
        return "Increase timeout setting or check target service health"
    elif "not found" in cause.lower():
        return f"Verify file path in step outputs or that {step.skill} is properly installed"
    elif "permission" in cause.lower():
        return "Run with appropriate permissions or check file ACLs"
    elif "memory" in cause.lower():
        return "Reduce batch size or process data in chunks"
    elif "network" in cause.lower():
        return "Check network connectivity and firewall rules"
    elif "invalid" in cause.lower():
        return "Validate input data format before processing"
    else:
        return "Check step configuration and skill documentation"


def format_failure_report(
    context: FailureContext,
    analysis: dict | None = None
) -> str:
    """Format a failure report as human-readable string."""
    lines = []
    lines.append("=" * 50)
    lines.append("FAILURE REPORT")
    lines.append("=" * 50)

    lines.append(f"\nFailed Step: {context.failed_step.step_id}")
    lines.append(f"Skill: {context.failed_step.skill}")
    lines.append(f"Action: {context.failed_step.action}")
    lines.append(f"Error: {type(context.error).__name__}: {context.error}")

    if analysis:
        lines.append(f"\nLikely Cause: {analysis.get('likely_cause', 'Unknown')}")
        lines.append(f"Suggested Fix: {analysis.get('suggested_fix', 'None')}")
        if analysis.get('is_known_issue'):
            lines.append(f"Recurrence: {analysis.get('recurrence_count', 0)} times (known issue)")

    if context.rollback_actions:
        lines.append(f"\nRollback Actions: {len(context.rollback_actions)}")
        for action in context.rollback_actions:
            lines.append(f"  - {action.action.value}: {action.target}")

    if context.partial_results:
        lines.append(f"\nPartial Results Available: {len(context.partial_results)}")

    lines.append("\n" + "=" * 50)

    return "\n".join(lines)

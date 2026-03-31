"""
Execution Engine.
Orchestrates the execution of skill-based tasks with progress tracking.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from datetime import datetime
import asyncio

from .models import (
    ExecutionPlan, ExecutionResult, ExecutionStep, StepResult,
    Task, ExecutionMode, FailureMode
)
from .progress import ProgressTracker, ProgressStatus, format_progress_display
from .failure import handle_failure, FailureContext, FailureResult, create_rollback_spec
from .retry import RetryConfig, RetryState, calculate_backoff_delay, BackoffStrategy


@dataclass
class ExecutorConfig:
    """Configuration for execution engine."""
    failure_mode: FailureMode = FailureMode.FAIL_SOFT
    max_parallelism: int = 4
    enable_retry: bool = True
    enable_rollback: bool = True
    continue_on_conflict: bool = True
    progress_callback: Optional[Callable] = None
    step_timeout_seconds: float = 300.0


@dataclass
class ExecutorState:
    """Runtime state during execution."""
    plan: ExecutionPlan
    tracker: ProgressTracker
    step_results: dict[str, StepResult] = field(default_factory=dict)
    partial_outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    rollback_actions: list = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


class ExecutionEngine:
    """
    Main execution engine for orchestrating skill-based task execution.

    Handles:
    - Sequential and parallel step execution
    - Progress tracking and reporting
    - Failure handling and rollback
    - Retry logic with backoff
    - Result aggregation
    """

    def __init__(self, config: ExecutorConfig | None = None):
        """Initialize execution engine."""
        self.config = config or ExecutorConfig()

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute a complete plan.

        Args:
            plan: The execution plan to run

        Returns:
            ExecutionResult with all step results and metadata
        """
        state = ExecutorState(
            plan=plan,
            tracker=ProgressTracker(total_steps=len(plan.steps))
        )

        # Set up progress callback
        if self.config.progress_callback:
            state.tracker.on_progress_update = self.config.progress_callback

        # Initialize step tracking
        for step in plan.steps:
            state.tracker.add_step(step.step_id, f"{step.skill}:{step.action}")

        # Execute based on mode
        try:
            if plan.mode == ExecutionMode.AUTO:
                await self._execute_auto(state)
            elif plan.mode == ExecutionMode.SUGGEST:
                await self._execute_suggest(state)
            elif plan.mode == ExecutionMode.PLAN:
                await self._execute_plan(state)
            elif plan.mode == ExecutionMode.THINK:
                await self._execute_think(state)
            elif plan.mode == ExecutionMode.ADAPTIVE:
                await self._execute_adaptive(state)
            else:
                await self._execute_default(state)

        except Exception as e:
            state.errors.append(str(e))

        # Build final result
        return self._build_result(state)

    async def _execute_auto(self, state: ExecutorState) -> None:
        """Auto mode: execute immediately."""
        await self._execute_steps(state)

    async def _execute_suggest(self, state: ExecutorState) -> None:
        """Suggest mode: show plan, wait for confirmation (simulated here)."""
        # In real implementation, would wait for user confirmation
        await self._execute_steps(state)

    async def _execute_plan(self, state: ExecutorState) -> None:
        """Plan mode: detailed planning then execution."""
        await self._execute_steps(state)

    async def _execute_think(self, state: ExecutorState) -> None:
        """Think mode: reason but don't execute (simulated as dry run)."""
        for step in state.plan.steps:
            state.tracker.add_step(step.step_id, f"{step.skill}:{step.action}")
            state.tracker.update_step_progress(step.step_id, 100, "Reasoning complete (dry run)")

    async def _execute_adaptive(self, state: ExecutorState) -> None:
        """Adaptive mode: re-plan on failures."""
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            try:
                await self._execute_steps(state)
                return
            except Exception as e:
                if attempt >= max_attempts:
                    raise
                # Attempt to re-plan (simplified)
                state.errors.append(f"Attempt {attempt} failed: {e}, re-planning...")

    async def _execute_default(self, state: ExecutorState) -> None:
        """Default execution mode."""
        await self._execute_steps(state)

    async def _execute_steps(self, state: ExecutorState) -> None:
        """Execute all steps in dependency order."""
        plan = state.plan

        # Group steps by parallel execution
        for group_idx, group in enumerate(plan.parallel_groups):
            group_steps = [s for s in plan.steps if s.step_id in group]

            if len(group_steps) == 1:
                # Sequential execution
                await self._execute_step(state, group_steps[0])
            else:
                # Parallel execution
                await self._execute_parallel_group(state, group_steps)

    async def _execute_parallel_group(
        self,
        state: ExecutorState,
        steps: list[ExecutionStep]
    ) -> None:
        """Execute multiple steps in parallel."""
        tasks = [self._execute_step(state, step) for step in steps]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_step(self, state: ExecutorState, step: ExecutionStep) -> None:
        """Execute a single step with retry and failure handling."""
        state.tracker.start_step(step.step_id)

        # Create step result tracking
        step_result = StepResult(
            step_id=step.step_id,
            skill=step.skill,
            action=step.action,
            status="running",
            start_time=datetime.now()
        )
        state.step_results[step.step_id] = step_result

        try:
            # Execute with retry if enabled
            if self.config.enable_retry:
                result = await self._execute_with_retry(state, step)
            else:
                result = await self._execute_step_direct(state, step)

            # Success
            step_result.status = "done"
            step_result.success = True
            step_result.output = result
            step_result.end_time = datetime.now()
            state.tracker.complete_step(step.step_id, success=True)
            state.partial_outputs[step.step_id] = result

        except Exception as e:
            # Handle failure
            step_result.status = "failed"
            step_result.success = False
            step_result.error = str(e)
            step_result.end_time = datetime.now()
            state.tracker.fail_step(step.step_id, str(e))
            state.errors.append(f"Step {step.step_id} failed: {e}")

            # Failure handling
            failure_result = await self._handle_step_failure(state, step, e)

            if not failure_result.recovered and self.config.failure_mode == FailureMode.FAIL_FAST:
                raise

    async def _execute_with_retry(
        self,
        state: ExecutorState,
        step: ExecutionStep
    ) -> Any:
        """Execute step with retry logic."""
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=1000.0,
            max_delay_ms=10000.0,
            backoff=BackoffStrategy.EXPONENTIAL_JITTER,
            retryable_errors=["timeout", "connection", "temporary"]
        )

        last_error = None
        attempt = 0

        while attempt < retry_config.max_attempts:
            attempt += 1
            try:
                return await self._execute_step_direct(state, step)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if retryable
                is_retryable = any(err in error_str for err in retry_config.retryable_errors)
                if not is_retryable or attempt >= retry_config.max_attempts:
                    raise

                # Calculate delay
                delay_ms = calculate_backoff_delay(
                    retry_config, attempt, retry_config.initial_delay_ms
                )
                await asyncio.sleep(delay_ms / 1000)

        raise last_error

    async def _execute_step_direct(self, state: ExecutorState, step: ExecutionStep) -> Any:
        """Direct step execution without retry."""
        # This would integrate with the actual skill execution system
        # For now, simulate execution
        await asyncio.sleep(0.1)  # Simulate work

        # In real implementation, would call the skill's execute method
        # skill_executor = get_skill_executor(step.skill)
        # return await skill_executor.execute(step.action, step.inputs)

        return {"status": "success", "step_id": step.step_id}

    async def _handle_step_failure(
        self,
        state: ExecutorState,
        step: ExecutionStep,
        error: Exception
    ) -> FailureResult:
        """Handle a step failure."""
        # Create rollback specs
        rollback_specs = create_rollback_spec(step, step.rollback_on)

        # Build failure context
        context = FailureContext(
            failed_step=step,
            error=error,
            plan=state.plan,
            completed_steps=list(state.step_results.values()),
            partial_results=state.partial_outputs,
            can_rollback=self.config.enable_rollback,
            rollback_actions=rollback_specs
        )

        # Handle failure based on mode
        return handle_failure(context, self.config.failure_mode)

    def _build_result(self, state: ExecutorState) -> ExecutionResult:
        """Build final execution result."""
        step_results = list(state.step_results.values())

        # Determine overall success
        success = all(r.success for r in step_results) and not state.errors

        return ExecutionResult(
            plan=state.plan,
            step_results=step_results,
            success=success,
            total_duration_ms=(
                (datetime.now() - state.started_at).total_seconds() * 1000
            ),
            start_time=state.started_at,
            end_time=datetime.now(),
            errors=state.errors,
            partial_results=state.partial_outputs
        )


async def execute_plan(
    plan: ExecutionPlan,
    config: ExecutorConfig | None = None,
    progress_callback: Callable | None = None
) -> ExecutionResult:
    """
    Convenience function to execute a plan.

    Args:
        plan: Execution plan to run
        config: Optional executor configuration
        progress_callback: Optional progress update callback

    Returns:
        ExecutionResult
    """
    executor = ExecutionEngine(config)
    if progress_callback:
        executor.config.progress_callback = progress_callback
    return await executor.execute(plan)


def format_execution_result(result: ExecutionResult) -> str:
    """Format execution result as human-readable string."""
    lines = []

    # Summary
    status = "SUCCESS" if result.success else "FAILED"
    lines.append(f"Execution {status}")
    lines.append(f"Completed: {result.completed_steps}/{len(result.step_results)} steps")

    if result.total_duration_ms:
        lines.append(f"Duration: {result.total_duration_ms / 1000:.2f}s")

    if result.errors:
        lines.append(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            lines.append(f"  - {error}")

    if result.partial_results:
        lines.append(f"\nPartial Results: {len(result.partial_results)}")

    # Step details
    lines.append("\nStep Results:")
    for step_result in result.step_results:
        icon = "X" if step_result.success else "!"
        lines.append(f"  [{icon}] {step_result.step_id}: {step_result.skill}:{step_result.action}")
        if step_result.error:
            lines.append(f"      Error: {step_result.error}")

    return "\n".join(lines)

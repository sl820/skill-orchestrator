"""
Control Flow Manager.
Handles sequential, parallel, conditional, and loop execution patterns.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
from .models import ExecutionStep, ExecutionPlan, DependencyType


class FlowType(Enum):
    """Types of control flow patterns."""
    SEQUENTIAL = "SEQUENTIAL"           # One after another
    PARALLEL = "PARALLEL"               # All at once
    PARALLEL_WITH_SYNC = "PARALLEL_WITH_SYNC"  # Parallel but wait at barrier
    CONDITIONAL = "CONDITIONAL"         # Branch based on condition
    LOOP = "LOOP"                       # Repeat until condition
    MAP = "MAP"                         # Apply to each item
    FILTER = "FILTER"                   # Process only matching items


@dataclass
class FlowCondition:
    """A condition for branching control flow."""
    expression: str                    # Simple expression like "count > 0"
    evaluator: Optional[Callable] = None  # Custom evaluator function
    description: str = ""


@dataclass
class FlowStep:
    """A step in a control flow graph."""
    step_id: str
    flow_type: FlowType
    steps: list[FlowStep] = field(default_factory=list)  # Child steps
    condition: Optional[FlowCondition] = None
    iterations_max: int = 10          # Max iterations for loops
    barrier: bool = False              # Sync barrier for parallel
    branch_on: Optional[str] = None   # Step ID to branch on


@dataclass
class ExecutionContext:
    """Runtime context for control flow execution."""
    variables: dict = field(default_factory=dict)  # Shared state
    loop_counters: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)     # Step results
    errors: list = field(default_factory=list)


def build_control_flow(plan: ExecutionPlan) -> FlowStep:
    """
    Build a control flow graph from an execution plan.

    Args:
        plan: The execution plan

    Returns:
        Root FlowStep of the control flow graph
    """
    # Group steps by parallel execution groups
    parallel_groups = plan.parallel_groups

    if not parallel_groups:
        # No groups means all sequential
        return _build_sequential_flow(plan.steps)

    # Build flow based on groups
    flow_steps = []
    for group in parallel_groups:
        group_steps = [s for s in plan.steps if s.step_id in group]

        if len(group_steps) == 1:
            # Single step, sequential
            flow_steps.append(_step_to_flow(group_steps[0]))
        else:
            # Multiple steps in parallel
            parallel_flow = FlowStep(
                step_id=f"parallel_{'_'.join(group)}",
                flow_type=FlowType.PARALLEL,
                steps=[_step_to_flow(s) for s in group_steps]
            )
            flow_steps.append(parallel_flow)

    if len(flow_steps) == 1:
        return flow_steps[0]

    # Wrap in sequential flow
    return FlowStep(
        step_id="root",
        flow_type=FlowType.SEQUENTIAL,
        steps=flow_steps
    )


def _build_sequential_flow(steps: list[ExecutionStep]) -> FlowStep:
    """Build a sequential flow from steps."""
    flow_steps = [_step_to_flow(s) for s in steps]
    return FlowStep(
        step_id="sequential_root",
        flow_type=FlowType.SEQUENTIAL,
        steps=flow_steps
    )


def _step_to_flow(step: ExecutionStep) -> FlowStep:
    """Convert an ExecutionStep to a FlowStep."""
    return FlowStep(
        step_id=step.step_id,
        flow_type=FlowType.SEQUENTIAL,  # Default to sequential
        steps=[]
    )


async def execute_flow(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> Any:
    """
    Execute a control flow graph.

    Args:
        flow: The flow to execute
        context: Execution context
        executor: Function to execute a single step

    Returns:
        Result of flow execution
    """
    if flow.flow_type == FlowType.SEQUENTIAL:
        return await _execute_sequential(flow, context, executor)

    elif flow.flow_type == FlowType.PARALLEL:
        return await _execute_parallel(flow, context, executor)

    elif flow.flow_type == FlowType.PARALLEL_WITH_SYNC:
        return await _execute_parallel_with_sync(flow, context, executor)

    elif flow.flow_type == FlowType.CONDITIONAL:
        return await _execute_conditional(flow, context, executor)

    elif flow.flow_type == FlowType.LOOP:
        return await _execute_loop(flow, context, executor)

    elif flow.flow_type == FlowType.MAP:
        return await _execute_map(flow, context, executor)

    elif flow.flow_type == FlowType.FILTER:
        return await _execute_filter(flow, context, executor)

    else:
        raise ValueError(f"Unknown flow type: {flow.flow_type}")


async def _execute_sequential(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> Any:
    """Execute steps sequentially."""
    result = None
    for step in flow.steps:
        result = await execute_flow(step, context, executor)
        context.results[step.step_id] = result
    return result


async def _execute_parallel(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> list[Any]:
    """Execute steps in parallel."""
    import asyncio

    tasks = [execute_flow(step, context, executor) for step in flow.steps]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, step in enumerate(flow.steps):
        context.results[step.step_id] = results[i]

    return results


async def _execute_parallel_with_sync(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> list[Any]:
    """Execute parallel steps with synchronization barrier."""
    import asyncio

    # Execute all in parallel
    tasks = [execute_flow(step, context, executor) for step in flow.steps]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Store results
    for i, step in enumerate(flow.steps):
        context.results[step.step_id] = results[i]

    # Wait at barrier if specified
    if flow.barrier:
        # In a real implementation, would wait for external signal
        pass

    return results


async def _execute_conditional(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> Any:
    """Execute based on condition."""
    if not flow.condition:
        return None

    if _evaluate_condition(flow.condition, context):
        # Execute true branch
        return await _execute_sequential(flow, context, executor)
    elif flow.steps and len(flow.steps) > 1:
        # Execute false branch (second step)
        return await execute_flow(flow.steps[1], context, executor)

    return None


async def _execute_loop(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> list[Any]:
    """Execute loop until condition is met."""
    results = []
    counter = context.loop_counters.get(flow.step_id, 0)

    while counter < flow.iterations_max:
        counter += 1
        context.loop_counters[flow.step_id] = counter

        # Check condition if exists
        if flow.condition:
            if not _evaluate_condition(flow.condition, context):
                break

        # Execute body
        for step in flow.steps:
            result = await execute_flow(step, context, executor)
            results.append(result)
            context.results[step.step_id] = result

    return results


async def _execute_map(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> list[Any]:
    """Execute step for each item in a collection."""
    items = context.variables.get("map_items", [])
    results = []

    for item in items:
        context.variables["current_item"] = item
        for step in flow.steps:
            result = await execute_flow(step, context, executor)
            results.append(result)

    return results


async def _execute_filter(
    flow: FlowStep,
    context: ExecutionContext,
    executor: Callable[[ExecutionStep], Any]
) -> list[Any]:
    """Execute step only for items matching condition."""
    items = context.variables.get("filter_items", [])
    results = []

    for item in items:
        context.variables["current_item"] = item

        # Check filter condition
        if flow.condition and _evaluate_condition(flow.condition, context):
            for step in flow.steps:
                result = await execute_flow(step, context, executor)
                results.append(result)

    return results


def _evaluate_condition(condition: FlowCondition, context: ExecutionContext) -> bool:
    """Evaluate a flow condition."""
    if condition.evaluator:
        return condition.evaluator(context)

    # Simple expression evaluation
    try:
        # Build evaluation namespace
        namespace = dict(context.variables)
        namespace.update(context.loop_counters)

        # Note: In production, use safer evaluation
        result = eval(condition.expression, {"__builtins__": {}}, namespace)
        return bool(result)

    except Exception:
        return False


def format_control_flow(flow: FlowStep, indent: int = 0) -> str:
    """Format control flow as human-readable tree."""
    prefix = "  " * indent
    lines = []

    if flow.flow_type == FlowType.SEQUENTIAL:
        lines.append(f"{prefix}SEQUENTIAL:")
        for step in flow.steps:
            lines.append(format_control_flow(step, indent + 1))

    elif flow.flow_type == FlowType.PARALLEL:
        lines.append(f"{prefix}PARALLEL:")
        for step in flow.steps:
            lines.append(format_control_flow(step, indent + 1))

    elif flow.flow_type == FlowType.CONDITIONAL:
        lines.append(f"{prefix}CONDITIONAL: {flow.condition.expression if flow.condition else ''}")
        for step in flow.steps:
            lines.append(format_control_flow(step, indent + 1))

    elif flow.flow_type == FlowType.LOOP:
        lines.append(f"{prefix}LOOP (max={flow.iterations_max}):")
        for step in flow.steps:
            lines.append(format_control_flow(step, indent + 1))

    else:
        lines.append(f"{prefix}{flow.flow_type.value}: {flow.step_id}")

    return "\n".join(lines)

"""
Cost Estimation System.
Estimates token, time, and resource costs for task execution.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .models import CostEstimate, Task, ExecutionPlan
from .config import COST_PRECISION, DEFAULT_COST_LIMITS


class CostCalculator:
    """
    Calculates estimated costs for task execution.

    Provides token, time, and resource cost estimates
    based on task characteristics and historical data.
    """

    # Base costs per capability type
    BASE_TOKEN_COSTS = {
        "pdf": 2000,
        "docx": 1500,
        "xlsx": 1800,
        "pptx": 2000,
        "frontend-design": 3000,
        "web-access": 2500,
        "api": 1000,
        "mcp": 800,
        "default": 1000
    }

    # Time estimates per capability (seconds)
    BASE_TIME_COSTS = {
        "pdf": 30,
        "docx": 20,
        "xlsx": 25,
        "pptx": 30,
        "frontend-design": 60,
        "web-access": 45,
        "api": 10,
        "mcp": 5,
        "default": 15
    }

    def __init__(self, historical_data: Optional[dict] = None):
        """
        Initialize cost calculator.

        Args:
            historical_data: Historical cost data for refinement
        """
        self.historical_data = historical_data or {}

    def estimate_task_cost(self, task: Task, plan: ExecutionPlan) -> CostEstimate:
        """
        Estimate cost for a complete task execution plan.

        Args:
            task: The task to estimate
            plan: The execution plan

        Returns:
            CostEstimate with breakdown
        """
        breakdown = {}

        total_tokens = 0
        total_time = 0.0
        total_api_calls = 0
        total_filesystem = 0

        # Estimate per step
        for step in plan.steps:
            step_cost = self._estimate_step_cost(step.skill, step.action)
            breakdown[step.step_id] = step_cost

            total_tokens += step_cost.token_estimate
            total_time += step_cost.time_estimate_seconds
            total_api_calls += step_cost.external_api_calls
            total_filesystem += step_cost.filesystem_ops

        # Determine precision based on available data
        precision = self._determine_precision(plan)

        # Calculate confidence based on historical data
        confidence = self._calculate_cost_confidence(plan)

        return CostEstimate(
            token_estimate=total_tokens,
            time_estimate_seconds=total_time,
            external_api_calls=total_api_calls,
            filesystem_ops=total_filesystem,
            precision=precision,
            confidence=confidence,
            breakdown=breakdown
        )

    def _estimate_step_cost(self, skill: str, action: str) -> CostEstimate:
        """Estimate cost for a single step."""
        # Base cost lookup
        base_tokens = self.BASE_TOKEN_COSTS.get(skill, self.BASE_TOKEN_COSTS["default"])
        base_time = self.BASE_TIME_COSTS.get(skill, self.BASE_TIME_COSTS["default"])

        # Action multipliers
        action_multiplier = self._get_action_multiplier(action)

        # Check historical data for skill
        history_key = f"skill:{skill}"
        if history_key in self.historical_data:
            hist = self.historical_data[history_key]
            avg_tokens = hist.get("avg_tokens", base_tokens)
            avg_time = hist.get("avg_time", base_time)
        else:
            avg_tokens = base_tokens
            avg_time = base_time

        return CostEstimate(
            token_estimate=int(avg_tokens * action_multiplier),
            time_estimate_seconds=avg_time * action_multiplier,
            external_api_calls=self._estimate_api_calls(skill, action),
            filesystem_ops=self._estimate_filesystem_ops(action),
            precision="ESTIMATE",
            confidence=0.5,
            breakdown={
                "skill": skill,
                "action": action,
                "action_multiplier": action_multiplier
            }
        )

    def _get_action_multiplier(self, action: str) -> float:
        """Get cost multiplier based on action type."""
        multipliers = {
            "read": 0.5,
            "extract": 0.6,
            "analyze": 1.0,
            "create": 1.5,
            "generate": 1.5,
            "write": 1.5,
            "modify": 1.2,
            "update": 1.2,
            "delete": 0.8,
            "send": 1.0,
            "fetch": 0.5
        }
        return multipliers.get(action.lower(), 1.0)

    def _estimate_api_calls(self, skill: str, action: str) -> int:
        """Estimate number of external API calls."""
        api_skills = {"web-access", "api", "mcp"}
        if skill in api_skills:
            return 1
        return 0

    def _estimate_filesystem_ops(self, action: str) -> int:
        """Estimate number of filesystem operations."""
        fs_actions = {"create", "write", "read", "extract", "modify"}
        if action.lower() in fs_actions:
            return 1
        return 0

    def _determine_precision(self, plan: ExecutionPlan) -> str:
        """Determine estimation precision based on data availability."""
        if not self.historical_data:
            return "ESTIMATE"

        # Check how many skills have historical data
        known_skills = 0
        for step in plan.steps:
            if f"skill:{step.skill}" in self.historical_data:
                known_skills += 1

        ratio = known_skills / len(plan.steps) if plan.steps else 0

        if ratio >= 0.8:
            return "PRECISE"
        elif ratio >= 0.5:
            return "FORECAST"
        else:
            return "ESTIMATE"

    def _calculate_cost_confidence(self, plan: ExecutionPlan) -> float:
        """Calculate confidence in cost estimate."""
        if not self.historical_data:
            return 0.3

        known_skills = sum(
            1 for step in plan.steps
            if f"skill:{step.skill}" in self.historical_data
        )

        if not plan.steps:
            return 0.5

        return min(0.9, 0.3 + (known_skills / len(plan.steps)) * 0.6)


def format_cost_estimate(estimate: CostEstimate) -> str:
    """Format cost estimate as human-readable string."""
    lines = []
    lines.append("Cost Estimate:")

    # Main estimates
    lines.append(f"  Tokens: ~{estimate.token_estimate:,}")
    lines.append(f"  Time: ~{estimate.time_estimate_seconds:.0f}s")
    lines.append(f"  API Calls: {estimate.external_api_calls}")
    lines.append(f"  Filesystem Ops: {estimate.filesystem_ops}")

    # Precision and confidence
    lines.append(f"  Precision: {estimate.precision}")
    lines.append(f"  Confidence: {estimate.confidence:.0%}")

    # Breakdown if available
    if estimate.breakdown:
        lines.append("  Step Breakdown:")
        for step_id, cost in estimate.breakdown.items():
            if isinstance(cost, CostEstimate):
                lines.append(f"    {step_id}: {cost.token_estimate} tokens, {cost.time_estimate_seconds:.0f}s")

    return "\n".join(lines)


def check_cost_limits(
    estimate: CostEstimate,
    limits: Optional[dict] = None
) -> tuple[bool, list[str]]:
    """
    Check if estimate exceeds cost limits.

    Args:
        estimate: The cost estimate to check
        limits: Optional custom limits (uses DEFAULT_COST_LIMITS if not provided)

    Returns:
        Tuple of (within_limits, list of violations)
    """
    limits = limits or DEFAULT_COST_LIMITS
    violations = []

    if estimate.token_estimate > limits.get("max_tokens", float('inf')):
        violations.append(
            f"Token estimate ({estimate.token_estimate:,}) exceeds limit ({limits.get('max_tokens', 'unlimited')})"
        )

    if estimate.time_estimate_seconds > limits.get("max_time_seconds", float('inf')):
        violations.append(
            f"Time estimate ({estimate.time_estimate_seconds:.0f}s) exceeds limit ({limits.get('max_time_seconds', 'unlimited')}s)"
        )

    if estimate.external_api_calls > limits.get("max_api_calls", float('inf')):
        violations.append(
            f"API calls ({estimate.external_api_calls}) exceeds limit ({limits.get('max_api_calls', 'unlimited')})"
        )

    return len(violations) == 0, violations

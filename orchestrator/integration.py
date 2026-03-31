"""
Main Orchestrator Class.
Unified interface for skill orchestration with all capabilities.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
import json

from .models import (
    Task, ExecutionPlan, ExecutionResult, ExecutionStep,
    SkillMatch, Capability, ExecutionMode, RiskAssessment,
    CostEstimate
)
from .decomposition import decompose_task, format_task_decomposition
from .mapping import find_skill_for_capability, CAPABILITY_MAP
from .scoring import calculate_confidence, get_confidence_level
from .conflict import resolve_conflict, detect_potential_conflicts
from .risk import assess_risk, select_execution_mode, format_risk_assessment
from .dependency_graph import DependencyGraph, format_dependency_graph
from .executor import ExecutionEngine, ExecutorConfig, format_execution_result
from .preferences import PreferenceStore
from .cost import CostCalculator, format_cost_estimate, check_cost_limits
from .versioning import VersionTracker


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    skills_base_path: str = "skills"
    preferences_path: Optional[str] = None
    enable_auto_decomposition: bool = True
    enable_cost_estimation: bool = True
    enable_version_tracking: bool = True
    max_plan_retries: int = 3
    on_progress: Optional[Callable] = None


class SkillOrchestrator:
    """
    Main orchestrator class.

    Provides unified interface for:
    - Task decomposition
    - Skill matching
    - Execution planning
    - Risk assessment
    - Plan execution
    - Cost estimation
    - User preference learning
    """

    def __init__(self, config: OrchestratorConfig | None = None):
        """
        Initialize the orchestrator.

        Args:
            config: Optional orchestrator configuration
        """
        self.config = config or OrchestratorConfig()

        # Initialize components
        self.executor = ExecutionEngine()
        self.preferences = PreferenceStore(self.config.preferences_path)
        self.cost_calculator = CostCalculator()
        self.version_tracker = VersionTracker(self.config.skills_base_path)

        # Cache for discovered skills
        self._skill_cache: dict[str, Any] = {}

    def plan(self, request: str) -> ExecutionPlan:
        """
        Create an execution plan for a user request.

        Args:
            request: User's request string

        Returns:
            ExecutionPlan ready for execution
        """
        # Step 1: Decompose task
        task = decompose_task(request)
        if not task.original_request:
            task.original_request = request

        # Step 2: Match skills to capabilities
        skill_matches = self._match_capabilities(task.capabilities_needed)

        # Step 3: Detect conflicts
        conflicts = detect_potential_conflicts(skill_matches)
        for conflict in conflicts:
            resolved = resolve_conflict(conflict[0], conflict[1])
            # Handle conflict resolution

        # Step 4: Assess risk
        risk = assess_risk(task, skill_matches)

        # Step 5: Select execution mode
        has_missing = any(m.match_type.name == "MISSING" for m in skill_matches)
        mode = select_execution_mode(
            risk.overall_score,
            has_missing,
            request
        )

        # Step 6: Build execution steps
        steps = self._build_execution_steps(skill_matches, task)

        # Step 7: Build dependency graph
        graph = DependencyGraph()
        for step in steps:
            graph.add_step(step)

        # Get parallel execution groups
        parallel_groups = graph.topological_sort()

        # Step 8: Create plan
        plan = ExecutionPlan(
            task=task,
            mode=mode,
            steps=steps,
            skill_matches=skill_matches,
            gaps=[m for m in skill_matches if m.match_type.name == "MISSING"],
            risk=risk,
            conflicts=[],
            parallel_groups=parallel_groups
        )

        # Step 9: Estimate cost
        if self.config.enable_cost_estimation:
            cost = self.cost_calculator.estimate_task_cost(task, plan)
            plan.estimated_cost = {
                "token_estimate": cost.token_estimate,
                "time_estimate_seconds": cost.time_estimate_seconds
            }

        return plan

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute a plan.

        Args:
            plan: Execution plan to run

        Returns:
            ExecutionResult with execution details
        """
        if self.config.on_progress:
            self.executor.config.progress_callback = self.config.on_progress

        result = await self.executor.execute(plan)

        # Learn from execution
        self._learn_from_execution(plan, result)

        return result

    def plan_and_execute(self, request: str) -> tuple[ExecutionPlan, ExecutionResult]:
        """
        Create and execute a plan in one go.

        Args:
            request: User's request string

        Returns:
            Tuple of (ExecutionPlan, ExecutionResult)
        """
        import asyncio
        plan = self.plan(request)
        result = asyncio.run(self.execute(plan))
        return plan, result

    def _match_capabilities(self, capabilities: list[Capability]) -> list[SkillMatch]:
        """Match capabilities to skills."""
        # Get available skills from capability map
        available_skills = list(CAPABILITY_MAP.keys())
        matches = []
        for cap in capabilities:
            # find_skill_for_capability already returns SkillMatch
            skill_match = find_skill_for_capability(cap.name, available_skills)
            matches.append(skill_match)

        return matches

    def _build_execution_steps(
        self,
        skill_matches: list[SkillMatch],
        task: Task
    ) -> list[ExecutionStep]:
        """Build execution steps from skill matches."""
        steps = []

        for i, match in enumerate(skill_matches):
            if not match.skill:
                continue

            step = ExecutionStep(
                step_id=f"step_{i + 1}",
                skill=match.skill.name,
                action=match.capability.action or "execute",
                inputs={},
                outputs={},
                dependencies=[]
            )

            # Add dependencies based on data flow
            for prev_match in skill_matches[:i]:
                if prev_match.skill and self._has_data_dependency(prev_match, match):
                    step.dependencies.append(f"step_{skill_matches.index(prev_match) + 1}")

            steps.append(step)

        return steps

    def _has_data_dependency(self, from_match: SkillMatch, to_match: SkillMatch) -> bool:
        """Check if there's a data dependency between skill matches."""
        # Check if output of from_match feeds into to_match
        from_cap = from_match.capability.name
        to_cap = to_match.capability.name

        # Document processing chain
        document_chain = ["pdf", "docx", "xlsx", "pptx"]
        if from_cap in document_chain and to_cap in document_chain:
            return True

        # Any to analysis
        if from_cap in document_chain and to_cap in ["analysis", "report"]:
            return True

        return False

    def _learn_from_execution(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        """Update preferences based on execution results."""
        for step_result in result.step_results:
            # Find corresponding skill match
            for match in plan.skill_matches:
                if match.skill and match.skill.name == step_result.skill:
                    # Record implicit preference
                    self.preferences.add_implicit_preference(
                        skill=step_result.skill,
                        capability=match.capability.name,
                        success=step_result.success,
                        context={"action": step_result.action}
                    )

    def get_skill_info(self, skill_name: str) -> dict:
        """Get information about a skill."""
        return {
            "name": skill_name,
            "version": self.version_tracker.get_version_info(skill_name),
            "preference": self.preferences.get_skill_preference(skill_name),
            "capabilities": CAPABILITY_MAP.get(skill_name, {}).get("capabilities", [])
        }

    def list_capabilities(self) -> list[str]:
        """List all available capabilities."""
        return list(CAPABILITY_MAP.keys())

    def format_plan_summary(self, plan: ExecutionPlan) -> str:
        """Format execution plan as human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("EXECUTION PLAN")
        lines.append("=" * 60)

        lines.append(f"\nTask: {plan.task.goal}")
        lines.append(f"Mode: {plan.mode.value}")
        lines.append(f"Risk: {plan.risk.risk_level.value} ({plan.risk.overall_score:.2f})")

        if plan.gaps:
            lines.append(f"\nWarning: {len(plan.gaps)} capabilities not available")

        lines.append(f"\nSteps ({len(plan.steps)}):")
        for i, step in enumerate(plan.steps):
            deps = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
            lines.append(f"  {i + 1}. [{step.step_id}] {step.skill}:{step.action}{deps}")

        lines.append(f"\nParallel Groups: {len(plan.parallel_groups)}")
        for i, group in enumerate(plan.parallel_groups):
            lines.append(f"  Group {i + 1}: {', '.join(group)}")

        if plan.estimated_cost:
            lines.append(f"\nEstimated Cost:")
            lines.append(f"  Tokens: {plan.estimated_cost.get('token_estimate', 'N/A')}")
            lines.append(f"  Time: {plan.estimated_cost.get('time_estimate_seconds', 'N/A')}s")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


def create_orchestrator(
    skills_path: str = "skills",
    preferences_path: str = ".skill_preferences.json"
) -> SkillOrchestrator:
    """
    Factory function to create an orchestrator instance.

    Args:
        skills_path: Path to skills directory
        preferences_path: Path to preferences file

    Returns:
        Configured SkillOrchestrator instance
    """
    config = OrchestratorConfig(
        skills_base_path=skills_path,
        preferences_path=preferences_path
    )
    return SkillOrchestrator(config)

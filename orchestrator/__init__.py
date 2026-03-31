"""
Skill Orchestrator - Production-grade skill orchestration engine.

A meta-skill that sits between the user and all other skills,
acting as an intelligent router and execution planner.
"""

__version__ = "1.0.0"

import os
import json

# Timeout for subprocess calls (seconds)
_SUBPROCESS_TIMEOUT = 30

from .models import (
    Task,
    InputSpec,
    OutputSpec,
    Capability,
    SkillMatch,
    SkillInfo,
    ExecutionStep,
    ExecutionPlan,
    ExecutionResult,
    StepResult,
    RiskAssessment,
    DependencyType,
    ExecutionMode,
    FailureMode,
    ConfidenceLevel,
    RiskLevel,
    GapSeverity,
    MatchType,
    VersionInfo,
    CompatibilityInfo,
    BreakingChange,
    UserPreference,
    CostEstimate,
    ConflictResolution,
)

from .config import (
    CONFIDENCE_WEIGHTS,
    RISK_WEIGHTS,
    EXECUTION_MODE_THRESHOLDS,
    CONFLICT_THRESHOLDS,
    RISK_LEVELS,
    REVERSIBILITY_LEVELS,
    EXCELLENCE_LEVELS,
    GAP_SEVERITY,
    INCOMPATIBLE_COMBINATIONS,
    PREFERENCE_SIGNALS,
    COST_PRECISION,
    DEFAULT_COST_LIMITS,
    BREAKING_CHANGE_SEVERITY,
)

from .mapping import (
    CAPABILITY_MAP,
    find_skill_for_capability,
    list_all_capabilities,
    get_capability_keywords,
    get_skill_description,
    is_skill_incompatible,
)
from .decomposition import (
    decompose_task,
    decompose_task_simple,
    extract_inputs_outputs,
    infer_capabilities,
    format_task_decomposition,
)

from .scoring import (
    calculate_confidence,
    get_confidence_level,
    format_confidence_breakdown,
)

from .conflict import (
    resolve_conflict,
    format_conflict_display,
    detect_potential_conflicts,
)

from .risk import (
    assess_risk,
    select_execution_mode,
    format_risk_assessment,
)

from .dependency_graph import (
    DependencyGraph,
    format_dependency_graph,
)

from .retry import (
    RetryConfig,
    RetryState,
    BackoffStrategy,
    calculate_backoff_delay,
    format_retry_config,
)

from .failure import (
    RollbackAction,
    RollbackSpec,
    FailureContext,
    FailureResult,
    create_rollback_spec,
    handle_failure,
    analyze_failure,
    format_failure_report,
)

from .control_flow import (
    FlowType,
    FlowCondition,
    FlowStep,
    ExecutionContext,
    build_control_flow,
    execute_flow,
    format_control_flow,
)

from .progress import (
    ProgressStatus,
    ProgressStep,
    ProgressTracker,
    format_progress_display,
)

from .executor import (
    ExecutorConfig,
    ExecutorState,
    ExecutionEngine,
    execute_plan,
    format_execution_result,
)

from .preferences import (
    PreferenceStore,
    format_preference_display,
)

from .cost import (
    CostCalculator,
    format_cost_estimate,
    check_cost_limits,
)

from .versioning import (
    VersionTracker,
    parse_version,
    compare_versions,
    get_update_type,
    detect_breaking_changes,
    format_version_info,
)

from .integration import (
    SkillOrchestrator,
    OrchestratorConfig,
    create_orchestrator,
)

from .post_execution import (
    PostExecutionConfig,
    PostExecutionHandler,
    format_execution_summary,
)

from .cli import main as cli_main


def invoke(request: str = "") -> dict:
    """
    Auto-execution entry point for skill-orchestrator.

    This function is called automatically when the skill is triggered,
    executing the full workflow: scan skills → analyze request → match
    capabilities → build plan → return results.

    Args:
        request: Optional user request string

    Returns:
        dict with execution results containing:
        - skills: list of installed skills
        - mcp_servers: list of MCP servers found
        - plan: execution plan (if request provided)
        - error: error message (if any)
    """
    result = {
        "skills": [],
        "mcp_servers": [],
        "plan": None,
        "error": None,
    }

    # Step 1: Scan installed skills using scan_all() directly
    try:
        from scripts.scan_skills import scan_all
        scan_data = scan_all()
        result["skills"] = scan_data.get("skills", {}).get("skills", [])
        result["mcp_servers"] = scan_data.get("mcp", {}).get("servers", [])
    except Exception as e:
        result["error"] = f"Failed to scan skills: {e}"

    # Step 2: If request provided, create execution plan
    if request and not result["error"]:
        try:
            from .integration import create_orchestrator

            orchestrator = create_orchestrator()

            # Create plan
            plan = orchestrator.plan(request)

            # Format plan summary
            plan_summary = orchestrator.format_plan_summary(plan)

            # Convert plan to dict for JSON serialization
            plan_dict = {
                "task_goal": plan.task.goal,
                "mode": plan.mode.value,
                "risk_level": plan.risk.risk_level.value,
                "risk_score": plan.risk.overall_score,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "skill": s.skill,
                        "action": s.action,
                        "dependencies": s.dependencies,
                    }
                    for s in plan.steps
                ],
                "gaps": [
                    {"capability": g.capability.name, "severity": g.match_type.value}
                    for g in plan.gaps
                ],
                "parallel_groups": plan.parallel_groups,
                "estimated_cost": plan.estimated_cost,
                "formatted": plan_summary,
            }
            result["plan"] = plan_dict

        except Exception as e:
            result["error"] = f"Failed to create execution plan: {e}"

    return result


async def invoke_async(request: str = "") -> dict:
    """
    Async version of invoke() for use in async contexts.

    Args:
        request: Optional user request string

    Returns:
        dict with execution results
    """
    import asyncio
    return await asyncio.to_thread(invoke, request)


def main():
    """
    CLI entry point that can be called from SKILL.md.

    This function is registered as the skill's execution entry point
    and is called when the skill is invoked without arguments.
    """
    print("🔍 扫描已安装的 Skills...")
    print()

    try:
        from scripts.scan_skills import scan_all
        data = scan_all()
        skills = data.get("skills", {})
        mcp = data.get("mcp", {})
        print(f"Skills: {skills.get('total', 0)} installed | MCP: {mcp.get('total_servers', 0)} servers, {len(mcp.get('tools', []))} tools")
        for skill in skills.get("skills", [])[:10]:
            print(f"  * {skill['name']}")
        if skills.get("total", 0) > 10:
            print(f"  ... and {skills.get('total', 0) - 10} more")
    except Exception as e:
        print(f"❌ 扫描失败: {e}")

    print()
    print("💡 使用方式:")
    print("   /skill-orchestrator <your request>")
    print()
    print("   例如:")
    print("   /skill-orchestrator 帮我分析这个CSV文件并生成图表")
    print()


__all__ = [
    # Version
    "__version__",
    # Models
    "Task",
    "InputSpec",
    "OutputSpec",
    "Capability",
    "SkillMatch",
    "ExecutionStep",
    "ExecutionPlan",
    "ExecutionResult",
    "StepResult",
    "RiskAssessment",
    "DependencyType",
    "ExecutionMode",
    "FailureMode",
    "ConfidenceLevel",
    "RiskLevel",
    "GapSeverity",
    "MatchType",
    "SkillInfo",
    "VersionInfo",
    "CompatibilityInfo",
    "BreakingChange",
    "UserPreference",
    "CostEstimate",
    "ConflictResolution",
    # Config
    "CONFIDENCE_WEIGHTS",
    "RISK_WEIGHTS",
    "EXECUTION_MODE_THRESHOLDS",
    "CONFLICT_THRESHOLDS",
    "RISK_LEVELS",
    "REVERSIBILITY_LEVELS",
    "EXCELLENCE_LEVELS",
    "GAP_SEVERITY",
    "INCOMPATIBLE_COMBINATIONS",
    "PREFERENCE_SIGNALS",
    "COST_PRECISION",
    "DEFAULT_COST_LIMITS",
    "BREAKING_CHANGE_SEVERITY",
    # Functions
    "find_skill_for_capability",
    "decompose_task",
    "decompose_task_simple",
    "extract_inputs_outputs",
    "infer_capabilities",
    "format_task_decomposition",
    "list_all_capabilities",
    "get_capability_keywords",
    "get_skill_description",
    "is_skill_incompatible",
    # Scoring
    "calculate_confidence",
    "get_confidence_level",
    "format_confidence_breakdown",
    # Conflict Resolution
    "resolve_conflict",
    "format_conflict_display",
    "detect_potential_conflicts",
    # Risk Assessment
    "assess_risk",
    "select_execution_mode",
    "format_risk_assessment",
    # Dependency Graph
    "DependencyGraph",
    "format_dependency_graph",
    # Retry
    "RetryConfig",
    "RetryState",
    "BackoffStrategy",
    "calculate_backoff_delay",
    "format_retry_config",
    # Failure Handling
    "RollbackAction",
    "RollbackSpec",
    "FailureContext",
    "FailureResult",
    "create_rollback_spec",
    "handle_failure",
    "analyze_failure",
    "format_failure_report",
    # Control Flow
    "FlowType",
    "FlowCondition",
    "FlowStep",
    "ExecutionContext",
    "build_control_flow",
    "execute_flow",
    "format_control_flow",
    # Progress Tracking
    "ProgressStatus",
    "ProgressStep",
    "ProgressTracker",
    "format_progress_display",
    # Executor
    "ExecutorConfig",
    "ExecutorState",
    "ExecutionEngine",
    "execute_plan",
    "format_execution_result",
    # Preferences
    "PreferenceStore",
    "format_preference_display",
    # Cost Estimation
    "CostCalculator",
    "format_cost_estimate",
    "check_cost_limits",
    # Versioning
    "VersionTracker",
    "parse_version",
    "compare_versions",
    "get_update_type",
    "detect_breaking_changes",
    "format_version_info",
    # Integration
    "SkillOrchestrator",
    "OrchestratorConfig",
    "create_orchestrator",
    # Post-Execution
    "PostExecutionConfig",
    "PostExecutionHandler",
    "format_execution_summary",
    # Auto-execution entry point
    "invoke",
    "invoke_async",
    "main",
]

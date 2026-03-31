"""
CLI Interface for Skill Orchestrator.
Command-line interface for plan creation and execution.
"""

from __future__ import annotations
import argparse
import asyncio
import sys
from typing import Optional

from .integration import SkillOrchestrator, create_orchestrator
from .models import ExecutionMode


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Skill Orchestrator - Intelligent skill execution planner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Create execution plan")
    plan_parser.add_argument("request", help="User request string")
    plan_parser.add_argument("--format", "-f", choices=["text", "json"], default="text",
                            help="Output format")

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Plan and execute request")
    exec_parser.add_argument("request", help="User request string")
    exec_parser.add_argument("--mode", "-m", choices=["auto", "suggest", "plan", "think"],
                            help="Execution mode override")
    exec_parser.add_argument("--output", "-o", help="Output file for results")

    # List capabilities command
    list_parser = subparsers.add_parser("list", help="List available capabilities")
    list_parser.add_argument("--skills", action="store_true", help="List installed skills")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get skill information")
    info_parser.add_argument("skill", help="Skill name")

    # Version command
    version_parser = subparsers.add_parser("version", help="Version information")
    version_parser.add_argument("skill", nargs="?", help="Skill name (optional)")

    return parser


def format_plan_text(plan) -> str:
    """Format plan as text."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXECUTION PLAN")
    lines.append("=" * 60)

    lines.append(f"\nTask: {plan.task.goal}")
    lines.append(f"Mode: {plan.mode.value}")
    lines.append(f"Risk Level: {plan.risk.risk_level.value}")
    lines.append(f"Risk Score: {plan.risk.overall_score:.2f}")

    if plan.risk.recommendations:
        lines.append("\nRecommendations:")
        for rec in plan.risk.recommendations:
            lines.append(f"  - {rec}")

    if plan.gaps:
        lines.append(f"\n[WARNING] Missing capabilities: {len(plan.gaps)}")
        for gap in plan.gaps:
            lines.append(f"  - {gap.capability.name}")

    lines.append(f"\nExecution Steps: {len(plan.steps)}")
    for i, step in enumerate(plan.steps, 1):
        deps = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
        lines.append(f"  {i}. [{step.step_id}] {step.skill}:{step.action}{deps}")

    lines.append(f"\nParallel Groups: {len(plan.parallel_groups)}")
    for i, group in enumerate(plan.parallel_groups):
        lines.append(f"  Group {i + 1}: {', '.join(group)}")

    if plan.estimated_cost:
        cost = plan.estimated_cost
        lines.append("\nEstimated Cost:")
        lines.append(f"  Tokens: {cost.get('token_estimate', 'N/A')}")
        lines.append(f"  Time: {cost.get('time_estimate_seconds', 'N/A')}s")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def format_result_text(result) -> str:
    """Format execution result as text."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXECUTION RESULT")
    lines.append("=" * 60)

    status = "SUCCESS" if result.success else "FAILED"
    lines.append(f"\nStatus: {status}")
    lines.append(f"Completed: {result.completed_steps}/{len(result.step_results)} steps")

    if result.total_duration_ms:
        lines.append(f"Duration: {result.total_duration_ms / 1000:.2f}s")

    if result.errors:
        lines.append(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            lines.append(f"  - {error}")

    lines.append("\nStep Results:")
    for step_result in result.step_results:
        icon = "X" if step_result.success else "!"
        status_icon = {
            "done": "[X]",
            "failed": "[!]",
            "skipped": "[-]",
            "running": "[>]"
        }.get(step_result.status, "[?]")

        lines.append(f"  {status_icon} {step_result.skill}:{step_result.action}")
        if step_result.error:
            lines.append(f"      Error: {step_result.error}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


async def handle_plan(args, orchestrator: SkillOrchestrator) -> int:
    """Handle plan command."""
    plan = orchestrator.plan(args.request)

    if args.format == "json":
        import json
        # Convert to dict for JSON serialization
        plan_dict = {
            "task": {"goal": plan.task.goal},
            "mode": plan.mode.value,
            "risk": {
                "level": plan.risk.risk_level.value,
                "score": plan.risk.overall_score
            },
            "steps": [
                {
                    "id": s.step_id,
                    "skill": s.skill,
                    "action": s.action,
                    "dependencies": s.dependencies
                }
                for s in plan.steps
            ],
            "parallel_groups": plan.parallel_groups
        }
        print(json.dumps(plan_dict, indent=2))
    else:
        print(format_plan_text(plan))

    return 0


async def handle_execute(args, orchestrator: SkillOrchestrator) -> int:
    """Handle execute command."""
    plan = orchestrator.plan(args.request)

    # Override mode if specified
    if args.mode:
        mode_map = {
            "auto": ExecutionMode.AUTO,
            "suggest": ExecutionMode.SUGGEST,
            "plan": ExecutionMode.PLAN,
            "think": ExecutionMode.THINK
        }
        plan.mode = mode_map.get(args.mode, plan.mode)

    print(format_plan_text(plan))

    # Execute plan
    print("\nExecuting plan...\n")
    result = await orchestrator.execute(plan)

    print(format_result_text(result))

    # Save to file if specified
    if args.output:
        import json
        result_dict = {
            "success": result.success,
            "completed_steps": result.completed_steps,
            "failed_steps": result.failed_steps,
            "duration_ms": result.total_duration_ms,
            "errors": result.errors,
            "step_results": [
                {
                    "skill": r.skill,
                    "action": r.action,
                    "status": r.status,
                    "success": r.success,
                    "error": r.error
                }
                for r in result.step_results
            ]
        }
        with open(args.output, 'w') as f:
            json.dump(result_dict, f, indent=2)
        print(f"\nResults saved to {args.output}")

    return 0 if result.success else 1


def handle_list(args, orchestrator: SkillOrchestrator) -> int:
    """Handle list command."""
    if args.skills:
        # List installed skills
        from .mapping import CAPABILITY_MAP
        print("Installed skills:")
        for skill_name in sorted(CAPABILITY_MAP.keys()):
            cap_info = CAPABILITY_MAP[skill_name]
            primary = cap_info.get("primary", "unknown")
            print(f"  - {skill_name} (primary: {primary})")
    else:
        # List capabilities
        caps = orchestrator.list_capabilities()
        print(f"Available capabilities ({len(caps)}):")
        for cap in sorted(caps):
            print(f"  - {cap}")

    return 0


def handle_info(args, orchestrator: SkillOrchestrator) -> int:
    """Handle info command."""
    info = orchestrator.get_skill_info(args.skill)

    print(f"Skill: {info['name']}")
    print(f"\nCapabilities:")
    for cap in info['capabilities']:
        print(f"  - {cap}")

    pref = info.get('preference', [])
    if pref:
        print(f"\nUser Preferences:")
        for p in pref:
            print(f"  - {p.capability}: {p.preference:+.2f}")

    return 0


def handle_version(args, orchestrator: SkillOrchestrator) -> int:
    """Handle version command."""
    from . import __version__

    print(f"Skill Orchestrator version {__version__}")

    if args.skill:
        info = orchestrator.version_tracker.get_version_info(args.skill)
        print(f"\nSkill: {args.skill}")
        print(f"  Installed: {info.installed_version}")
        print(f"  Source: {info.source}")

    return 0


async def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Create orchestrator
    orchestrator = create_orchestrator()

    # Route to handler
    if args.command == "plan":
        return await handle_plan(args, orchestrator)
    elif args.command == "execute":
        return await handle_execute(args, orchestrator)
    elif args.command == "list":
        return handle_list(args, orchestrator)
    elif args.command == "info":
        return handle_info(args, orchestrator)
    elif args.command == "version":
        return handle_version(args, orchestrator)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main(sys.argv[1:]))
    sys.exit(exit_code)

"""
Multi-dimensional Risk Assessment.
Calculates risk scores for task execution.
"""

from __future__ import annotations
from typing import Optional
from .models import RiskAssessment, RiskLevel, Task, SkillMatch, ExecutionMode
from .config import RISK_WEIGHTS, RISK_LEVELS, REVERSIBILITY_LEVELS, EXECUTION_MODE_THRESHOLDS

# Keyword sets for risk assessment (extracted to avoid recreation on each call)
CRITICAL_KEYWORDS = frozenset({
    "delete", "remove", "drop", "destroy", "rm -rf",
    "database", "production", "deploy", "security",
})
HIGH_KEYWORDS = frozenset({
    "write", "create", "modify", "update", "change",
    "file", "document", "email", "send",
})
MEDIUM_KEYWORDS = frozenset({
    "analyze", "review", "check", "validate",
})
READ_KEYWORDS = frozenset({"read", "get", "fetch", "extract", "analyze"})
AUTO_KEYWORDS = frozenset({"直接做", "执行吧", "auto", "do it", "go ahead"})
THINK_KEYWORDS = frozenset({"how would", "how to", "分析", "what if", "what would"})


def assess_risk(
    task: Task,
    skill_matches: list[SkillMatch],
    context: dict | None = None,
) -> RiskAssessment:
    """
    Assess risk for executing a task.

    Total Risk Score = (
      riskLevel × 0.30 +
      reversibility × 0.20 +
      crossSystem × 0.20 +
      skillCount × 0.15 +
      userExpertise × 0.15
    )

    Args:
        task: The task to assess
        skill_matches: Matched skills for the task
        context: Additional context (e.g., user expertise level)

    Returns:
        RiskAssessment with overall score and dimension breakdown
    """
    dimensions = {}

    # 1. Risk Level (based on task operations)
    risk_level = _assess_risk_level(task)
    dimensions["risk_level"] = risk_level

    # 2. Reversibility
    reversibility = _assess_reversibility(task, skill_matches)
    dimensions["reversibility"] = reversibility

    # 3. Cross-System (spans multiple domains?)
    cross_system = _assess_cross_system(task, skill_matches)
    dimensions["cross_system"] = cross_system

    # 4. Skill Count
    skill_count = len(skill_matches)
    dimensions["skill_count"] = skill_count

    # 5. User Expertise
    user_expertise = _assess_user_expertise(context)
    dimensions["user_expertise"] = user_expertise

    # Weighted sum
    overall = (
        risk_level["score"] * RISK_WEIGHTS["risk_level"]
        + reversibility["score"] * RISK_WEIGHTS["reversibility"]
        + cross_system["score"] * RISK_WEIGHTS["cross_system"]
        + (skill_count / 10.0) * RISK_WEIGHTS["skill_count"]  # Normalize to 0-1
        + user_expertise["score"] * RISK_WEIGHTS["user_expertise"]
    )

    # Determine risk level enum
    if overall <= 0.25:
        level = RiskLevel.LOW
    elif overall <= 0.5:
        level = RiskLevel.MEDIUM
    elif overall <= 0.75:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.CRITICAL

    # Generate recommendations
    recommendations = _generate_recommendations(risk_level, reversibility, cross_system)

    return RiskAssessment(
        overall_score=overall,
        risk_level=level,
        dimensions=dimensions,
        reversibility_score=reversibility["score"],
        recommendations=recommendations,
    )


def _assess_risk_level(task: Task) -> dict:
    """Assess the inherent risk level of the task operations."""
    goal_lower = task.goal.lower()

    # Critical risk indicators
    if any(kw in goal_lower for kw in CRITICAL_KEYWORDS):
        return {"score": RISK_LEVELS["CRITICAL"]["score"], "level": "CRITICAL"}

    # High risk indicators
    if any(kw in goal_lower for kw in HIGH_KEYWORDS):
        return {"score": RISK_LEVELS["HIGH"]["score"], "level": "HIGH"}

    # Medium risk indicators
    if any(kw in goal_lower for kw in MEDIUM_KEYWORDS):
        return {"score": RISK_LEVELS["MEDIUM"]["score"], "level": "MEDIUM"}

    # Default to LOW
    return {"score": RISK_LEVELS["LOW"]["score"], "level": "LOW"}


def _assess_reversibility(task: Task, skill_matches: list[SkillMatch]) -> dict:
    """Assess how easily changes can be reversed."""
    # File creation is semi-reversible
    if task.outputs:
        return {"score": REVERSIBILITY_LEVELS["SEMI_REVERSIBLE"]["score"], "level": "SEMI_REVERSIBLE"}

    # Read-only operations are easily reversible
    goal_lower = task.goal.lower()
    if any(kw in goal_lower for kw in READ_KEYWORDS):
        return {"score": REVERSIBILITY_LEVELS["EASILY_REVERSIBLE"]["score"], "level": "EASILY_REVERSIBLE"}

    return {"score": REVERSIBILITY_LEVELS["SEMI_REVERSIBLE"]["score"], "level": "SEMI_REVERSIBLE"}


def _assess_cross_system(task: Task, skill_matches: list[SkillMatch]) -> dict:
    """Assess whether task spans multiple systems/domains."""
    # Multiple skills typically means cross-system
    if len(skill_matches) >= 3:
        return {"score": 0.7, "level": "HIGH"}

    # Check capability domains
    domains = set()
    for match in skill_matches:
        if match.capability:
            cap = match.capability.name
            # Categorize by domain
            if cap in ["pdf", "docx", "xlsx", "pptx"]:
                domains.add("office")
            elif cap in ["frontend", "web-access"]:
                domains.add("web")
            elif cap in ["api", "mcp"]:
                domains.add("integration")

    if len(domains) >= 2:
        return {"score": 0.6, "level": "MEDIUM"}

    return {"score": 0.3, "level": "LOW"}


def _assess_user_expertise(context: dict | None) -> dict:
    """Assess user's assumed expertise level."""
    if not context:
        return {"score": 0.5, "level": "MEDIUM"}

    expertise = context.get("user_expertise", "medium")

    if expertise == "expert":
        return {"score": 0.2, "level": "LOW_RISK"}
    elif expertise == "intermediate":
        return {"score": 0.5, "level": "MEDIUM"}
    else:
        return {"score": 0.8, "level": "HIGH_RISK"}


def _generate_recommendations(
    risk_level: dict,
    reversibility: dict,
    cross_system: dict,
) -> list[str]:
    """Generate risk-based recommendations."""
    recommendations = []

    if risk_level["level"] == "CRITICAL":
        recommendations.append("CRITICAL risk level detected - require explicit user approval")
    elif risk_level["level"] == "HIGH":
        recommendations.append("HIGH risk operations detected - ensure user confirmation")

    if reversibility["level"] == "IRREVERSIBLE":
        recommendations.append("Irreversible operations present - create backups before proceeding")

    if cross_system["level"] == "HIGH":
        recommendations.append("Cross-system operations - verify compatibility between components")

    return recommendations


def select_execution_mode(
    risk_score: float,
    has_missing_capabilities: bool,
    user_request_type: str = "",
    explicit_user_directive: str = "",
) -> ExecutionMode:
    """
    Select appropriate execution mode based on risk and context.

    Mode selection rules (apply in order):
    1. If user says "直接做"/"执行吧"/"auto" → AUTO
    2. If any step has Critical risk → THINK
    3. If user asks how/would/analysis → THINK
    4. If any capability MISSING → PLAN
    5. Calculate risk score → select by threshold
    6. Default → SUGGEST
    """
    # Rule 1: Explicit user directive
    if any(kw in explicit_user_directive.lower() for kw in AUTO_KEYWORDS):
        return ExecutionMode.AUTO

    # Rule 2: Critical risk
    if risk_score >= 0.75:
        return ExecutionMode.THINK

    # Rule 3: User asking how/would
    if any(kw in user_request_type.lower() for kw in THINK_KEYWORDS):
        return ExecutionMode.THINK

    # Rule 4: Missing capabilities
    if has_missing_capabilities:
        return ExecutionMode.PLAN

    # Rule 5: Risk-based threshold
    if risk_score <= EXECUTION_MODE_THRESHOLDS["AUTO"]:
        return ExecutionMode.AUTO
    elif risk_score <= EXECUTION_MODE_THRESHOLDS["SUGGEST"]:
        return ExecutionMode.SUGGEST
    elif risk_score <= EXECUTION_MODE_THRESHOLDS["PLAN"]:
        return ExecutionMode.PLAN
    else:
        return ExecutionMode.THINK


def format_risk_assessment(assessment: RiskAssessment) -> str:
    """Format risk assessment as human-readable string."""
    lines = []
    lines.append("Risk Assessment:")
    lines.append(f"  Overall Score: {assessment.overall_score:.2f}")
    lines.append(f"  Risk Level: {assessment.risk_level.value}")

    lines.append("  Dimensions:")
    for name, data in assessment.dimensions.items():
        if isinstance(data, dict):
            lines.append(f"    {name}: {data.get('level', 'N/A')} ({data.get('score', 0):.2f})")
        else:
            lines.append(f"    {name}: {data}")

    if assessment.recommendations:
        lines.append("  Recommendations:")
        for rec in assessment.recommendations:
            lines.append(f"    - {rec}")

    return "\n".join(lines)

"""
Conflict Resolution Module.
Resolves conflicts when two skills compete for the same capability.
"""

from __future__ import annotations
from typing import Optional
from .models import SkillMatch, ConflictResolution, SkillInfo, MatchType
from .config import CONFLICT_WEIGHTS, CONFLICT_THRESHOLDS


def resolve_conflict(
    skill_a: SkillMatch,
    skill_b: SkillMatch,
    user_preferences: dict | None = None,
) -> ConflictResolution:
    """
    Resolve conflict between two skill matches.

    5-dimension scoring:
    Score = Precision×0.30 + Coverage×0.25 + Performance×0.20
          + UserPreference×0.15 + Recency×0.10

    Args:
        skill_a: First skill match
        skill_b: Second skill match
        user_preferences: User preference data

    Returns:
        ConflictResolution with recommended action
    """
    score_a = _calculate_conflict_score(skill_a, user_preferences)
    score_b = _calculate_conflict_score(skill_b, user_preferences)

    gap = abs(score_a - score_b)

    # Determine resolution mode
    if gap >= CONFLICT_THRESHOLDS["AUTO"]:
        mode = "AUTO"
        recommended = skill_a.skill.name if score_a > score_b else skill_b.skill.name
    elif gap >= CONFLICT_THRESHOLDS["HYBRID"]:
        mode = "HYBRID"
        recommended = skill_a.skill.name if score_a > score_b else skill_b.skill.name
    else:
        mode = "MANUAL"
        recommended = None

    return ConflictResolution(
        skill_a=skill_a,
        skill_b=skill_b,
        score_a=score_a,
        score_b=score_b,
        gap=gap,
        mode=mode,
        recommended=recommended,
        options=[skill_a.skill.name, skill_b.skill.name],
    )


def _calculate_conflict_score(
    skill_match: SkillMatch,
    user_preferences: dict | None = None,
) -> float:
    """
    Calculate conflict resolution score using 5 dimensions.

    Score = Precision×0.30 + Coverage×0.25 + Performance×0.20
          + UserPreference×0.15 + Recency×0.10
    """
    scores = {}

    # 1. Precision (match quality)
    precision = _get_precision_score(skill_match)
    scores["precision"] = precision

    # 2. Coverage (how well it covers the capability)
    coverage = skill_match.confidence
    scores["coverage"] = coverage

    # 3. Performance (estimated performance)
    performance = _get_performance_score(skill_match)
    scores["performance"] = performance

    # 4. User Preference
    preference = _get_user_preference_score(skill_match, user_preferences)
    scores["user_preference"] = preference

    # 5. Recency
    recency = _get_recency_score(skill_match, user_preferences)
    scores["recency"] = recency

    # Weighted sum
    total = (
        precision * CONFLICT_WEIGHTS["precision"]
        + coverage * CONFLICT_WEIGHTS["coverage"]
        + performance * CONFLICT_WEIGHTS["performance"]
        + preference * CONFLICT_WEIGHTS["user_preference"]
        + recency * CONFLICT_WEIGHTS["recency"]
    )

    return total


def _get_precision_score(skill_match: SkillMatch) -> float:
    """Get precision score based on match type."""
    if skill_match.match_type == MatchType.EXACT:
        return 1.0
    elif skill_match.match_type == MatchType.PRIMARY:
        return 0.9
    elif skill_match.match_type == MatchType.PARTIAL:
        return 0.7
    elif skill_match.match_type == MatchType.INFERRED:
        return 0.5
    else:
        return 0.2


def _get_performance_score(skill_match: SkillMatch) -> float:
    """Get estimated performance score."""
    if not skill_match.skill:
        return 0.0

    skill = skill_match.skill

    # Skill with eval is typically more reliable
    if skill.has_eval:
        return 0.9

    # Known skills get a boost
    known_skills = {"pdf", "xlsx", "pptx", "docx", "frontend-design", "web-access"}
    if skill.name in known_skills:
        return 0.8

    return 0.6


def _get_user_preference_score(
    skill_match: SkillMatch,
    user_preferences: dict | None,
) -> float:
    """Get score based on user preferences."""
    if not user_preferences or not skill_match.skill:
        return 0.5

    skill_name = skill_match.skill.name
    cap_name = skill_match.capability.name

    key = f"{cap_name}:{skill_name}"
    if key in user_preferences:
        pref = user_preferences[key]
        # Convert -1.0 to 1.0 range to 0.0 to 1.0 range
        return (pref.get("preference", 0) + 1) / 2

    return 0.5


def _get_recency_score(
    skill_match: SkillMatch,
    user_preferences: dict | None,
) -> float:
    """Get score based on recency of use."""
    if not user_preferences or not skill_match.skill:
        return 0.5

    skill_name = skill_match.skill.name
    key = f"skill:{skill_name}"

    if key in user_preferences:
        data = user_preferences[key]
        # Assume more recent is better
        last_used = data.get("last_used", 0)
        if last_used > 7:  # Used within last 7 days
            return 0.8
        elif last_used > 30:
            return 0.6

    return 0.5


def format_conflict_display(resolution: ConflictResolution) -> str:
    """Format conflict resolution as human-readable display."""
    lines = []
    lines.append("Skill Conflict:")

    # Skill A
    a_name = resolution.skill_a.skill.name if resolution.skill_a.skill else "N/A"
    a_type = resolution.skill_a.match_type.value
    a_stars = "★" * int(resolution.score_a * 5)
    lines.append(f"  {a_name}: {resolution.score_a:.2f} {a_stars} ({a_type})")

    # Skill B
    b_name = resolution.skill_b.skill.name if resolution.skill_b.skill else "N/A"
    b_type = resolution.skill_b.match_type.value
    lines.append(f"  {b_name}: {resolution.score_b:.2f}    ({b_type})")

    # Resolution
    lines.append(f"  Resolution: {resolution.mode} (gap: {resolution.gap:.2f})")

    if resolution.mode == "HYBRID" and resolution.recommended:
        lines.append(f"  [{resolution.recommended}] (recommended)")

    if resolution.mode == "MANUAL":
        lines.append("  Options:")
        for i, opt in enumerate(resolution.options, 1):
            lines.append(f"    [{i}] {opt}")

    return "\n".join(lines)


def detect_potential_conflicts(
    skill_matches: list[SkillMatch],
) -> list[tuple[SkillMatch, SkillMatch]]:
    """
    Detect potential conflicts in a list of skill matches.
    Returns pairs of skills that might conflict.
    """
    conflicts = []

    # Check for incompatible combinations
    from .mapping import is_skill_incompatible

    skills_used = [m.skill.name for m in skill_matches if m.skill]

    for i, match_a in enumerate(skill_matches):
        for match_b in skill_matches[i + 1 :]:
            if not match_a.skill or not match_b.skill:
                continue

            if is_skill_incompatible(match_a.skill.name, match_b.skill.name):
                conflicts.append((match_a, match_b))

    return conflicts

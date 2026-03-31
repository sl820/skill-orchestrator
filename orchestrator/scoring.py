"""
Confidence Scoring System.
5-factor weighted formula for skill matching confidence.
"""

from __future__ import annotations
from typing import Optional
from .models import SkillMatch, SkillInfo, Capability, ConfidenceLevel
from .config import CONFIDENCE_WEIGHTS, EXCELLENCE_LEVELS
from .mapping import CAPABILITY_MAP, get_capability_keywords

STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
})


def calculate_confidence(
    capability: Capability,
    skill: SkillInfo,
    historical_data: dict | None = None,
    context: dict | None = None,
) -> tuple[float, dict]:
    """
    Calculate confidence score using 5-factor weighted formula.

    Confidence = keywordScore×0.25 + semanticScore×0.25
              + historicalSuccess×0.25 + coverageScore×0.15
              + recencyBoost×0.10

    Args:
        capability: The capability being matched
        skill: The skill to evaluate
        historical_data: Historical success data for skill/capability pairs
        context: Execution context (e.g., user preferences)

    Returns:
        Tuple of (confidence_score, breakdown_dict)
    """
    breakdown = {}

    # 1. Keyword Score (0.0-1.0)
    keyword_score = _calculate_keyword_score(capability.name, skill)
    breakdown["keywordScore"] = keyword_score

    # 2. Semantic Score (0.0-1.0)
    semantic_score = _calculate_semantic_score(capability, skill)
    breakdown["semanticScore"] = semantic_score

    # 3. Historical Success (0.0-1.0)
    historical_score = _calculate_historical_score(
        capability.name, skill.name, historical_data
    )
    breakdown["historicalSuccess"] = historical_score

    # 4. Coverage Score (0.0-1.0)
    coverage_score = _calculate_coverage_score(capability, skill)
    breakdown["coverageScore"] = coverage_score

    # 5. Recency Boost (0.0-1.0)
    recency_score = _calculate_recency_score(skill, historical_data)
    breakdown["recencyBoost"] = recency_score

    # Weighted sum
    total = (
        keyword_score * CONFIDENCE_WEIGHTS["keyword"]
        + semantic_score * CONFIDENCE_WEIGHTS["semantic"]
        + historical_score * CONFIDENCE_WEIGHTS["historical"]
        + coverage_score * CONFIDENCE_WEIGHTS["coverage"]
        + recency_score * CONFIDENCE_WEIGHTS["recency"]
    )

    breakdown["total"] = total
    breakdown["weights"] = CONFIDENCE_WEIGHTS

    return total, breakdown


def _calculate_keyword_score(capability: str, skill: SkillInfo) -> float:
    """Score based on direct keyword match between capability and skill."""
    cap_lower = capability.lower()

    # Check if capability directly matches skill name
    if cap_lower == skill.name.lower():
        return 1.0

    # Check capability keywords
    cap_keywords = get_capability_keywords(capability)
    skill_keywords = [kw.lower() for kw in skill.keywords]

    # Direct keyword overlap
    overlap = set(cap_keywords) & set(skill_keywords)
    if overlap:
        return 0.7 + (0.3 * len(overlap) / max(len(cap_keywords), 1))

    # Check if skill name is in capability keywords
    if skill.name.lower() in cap_keywords:
        return 0.8

    # Check if capability is in skill keywords
    if cap_lower in skill_keywords:
        return 0.6

    return 0.3


def _calculate_semantic_score(capability: Capability, skill: SkillInfo) -> float:
    """Score based on semantic similarity."""
    cap_name = capability.name.lower()
    skill_name = skill.name.lower()
    skill_desc = skill.description.lower()

    # Direct match
    if cap_name == skill_name:
        return 1.0

    # Check CAPABILITY_MAP for primary skill
    if cap_name in CAPABILITY_MAP:
        mapping = CAPABILITY_MAP[cap_name]
        if mapping["primary"] == skill_name:
            return 0.9
        if mapping.get("alternative") == skill_name:
            return 0.7

    # Semantic similarity in description
    shared_words = _compute_shared_words(cap_name, skill_desc)
    if shared_words > 5:
        return 0.6 + min(0.3, shared_words * 0.05)

    return 0.4


def _calculate_historical_score(
    capability: str,
    skill_name: str,
    historical_data: dict | None,
) -> float:
    """Score based on historical success rate."""
    if not historical_data:
        return 0.5  # Default neutral score

    # Look for historical data
    key = f"{capability}:{skill_name}"
    if key in historical_data:
        data = historical_data[key]
        success_rate = data.get("success_rate", 0.5)
        return success_rate

    # Check generic skill history
    skill_key = f"skill:{skill_name}"
    if skill_key in historical_data:
        data = historical_data[skill_key]
        return data.get("success_rate", 0.5)

    return 0.5


def _calculate_coverage_score(capability: Capability, skill: SkillInfo) -> float:
    """Score based on how well skill covers all aspects of capability."""
    cap_name = capability.name.lower()

    if cap_name in CAPABILITY_MAP:
        mapping = CAPABILITY_MAP[cap_name]
        cap_keywords = set(mapping.get("keywords", []))
        skill_keywords = set(kw.lower() for kw in skill.keywords)

        if not cap_keywords:
            return 0.5

        overlap = cap_keywords & skill_keywords
        coverage = len(overlap) / len(cap_keywords)
        return 0.5 + (coverage * 0.5)

    return 0.5


def _calculate_recency_score(
    skill: SkillInfo,
    historical_data: dict | None,
) -> float:
    """Score based on recent usage (recency boost)."""
    if not historical_data:
        return 0.5

    skill_key = f"skill:{skill.name}"
    if skill_key in historical_data:
        data = historical_data[skill_key]
        last_used = data.get("last_used")
        if last_used:
            # Simple recency: if used in last 7 days, boost
            # In real implementation, would check actual dates
            return 0.7

    return 0.5


def _compute_shared_words(text1: str, text2: str) -> int:
    """Count shared significant words between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    words1 = words1 - STOPWORDS
    words2 = words2 - STOPWORDS

    return len(words1 & words2)


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Convert numeric score to confidence level enum."""
    pct = score * 100
    if pct >= 90:
        return ConfidenceLevel.EXCELLENT
    elif pct >= 70:
        return ConfidenceLevel.GOOD
    elif pct >= 50:
        return ConfidenceLevel.MODERATE
    elif pct >= 30:
        return ConfidenceLevel.WEAK
    else:
        return ConfidenceLevel.POOR


def format_confidence_breakdown(breakdown: dict) -> str:
    """Format confidence breakdown as human-readable string."""
    lines = []
    lines.append("Confidence Breakdown:")

    weights = breakdown.get("weights", CONFIDENCE_WEIGHTS)
    for factor in ["keywordScore", "semanticScore", "historicalSuccess", "coverageScore", "recencyBoost"]:
        score = breakdown.get(factor, 0)
        weight = weights.get(factor.replace("Score", "").lower(), 0)
        contribution = score * weight
        lines.append(f"  {factor}: {score:.2f} x {weight:.2f} = {contribution:.2f}")

    lines.append(f"  Total: {breakdown.get('total', 0):.2f}")
    lines.append(f"  Level: {get_confidence_level(breakdown.get('total', 0)).value}")

    return "\n".join(lines)

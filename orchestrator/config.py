"""
Configuration constants and weights extracted from SKILL.md.
Single source of truth for all tunable parameters.
"""

from enum import Enum

# =============================================================================
# Confidence Scoring Weights (SKILL.md Phase 2)
# =============================================================================

CONFIDENCE_WEIGHTS = {
    "keyword": 0.25,
    "semantic": 0.25,
    "historical": 0.25,
    "coverage": 0.15,
    "recency": 0.10,
}

# =============================================================================
# Conflict Resolution Scoring (SKILL.md Phase 2)
# =============================================================================

CONFLICT_WEIGHTS = {
    "precision": 0.30,
    "coverage": 0.25,
    "performance": 0.20,
    "user_preference": 0.15,
    "recency": 0.10,
}

CONFLICT_THRESHOLDS = {
    "AUTO": 0.30,   # gap >= 0.30
    "HYBRID": 0.15, # gap 0.15-0.30
    "MANUAL": 0.0,  # gap < 0.15
}

# =============================================================================
# Risk Assessment Weights (SKILL.md Phase 4)
# =============================================================================

RISK_WEIGHTS = {
    "risk_level": 0.30,
    "reversibility": 0.20,
    "cross_system": 0.20,
    "skill_count": 0.15,
    "user_expertise": 0.15,
}

RISK_LEVELS = {
    "LOW": {"score": 0.2, "description": "Read-only, no system modification, fully reversible"},
    "MEDIUM": {"score": 0.5, "description": "Minor side effects, semi-reversible"},
    "HIGH": {"score": 0.75, "description": "Significant changes, difficult to reverse"},
    "CRITICAL": {"score": 1.0, "description": "Irreversible, security-sensitive, production-impacting"},
}

REVERSIBILITY_LEVELS = {
    "EASILY_REVERSIBLE": {"score": 0.2, "description": "Can undo in one step, no side effects"},
    "SEMI_REVERSIBLE": {"score": 0.5, "description": "Can revert with effort, some side effects"},
    "DIFFICULT": {"score": 0.75, "description": "Requires manual intervention to undo"},
    "IRREVERSIBLE": {"score": 1.0, "description": "Cannot undo, permanent changes"},
}

# =============================================================================
# Execution Mode Thresholds (SKILL.md Phase 4)
# =============================================================================

EXECUTION_MODE_THRESHOLDS = {
    "AUTO": 0.25,
    "SUGGEST": 0.50,
    "PLAN": 0.75,
    "THINK": None,  # Special case: always available for explicit triggers
}

# =============================================================================
# Confidence Levels (SKILL.md Phase 2)
# =============================================================================

EXCELLENCE_LEVELS = {
    "EXCELLENT": {"min": 90, "max": 100},
    "GOOD": {"min": 70, "max": 89},
    "MODERATE": {"min": 50, "max": 69},
    "WEAK": {"min": 30, "max": 49},
    "POOR": {"min": 0, "max": 29},
}

# =============================================================================
# Gap Severity (SKILL.md Phase 2)
# =============================================================================

GAP_SEVERITY = {
    "BLOCKING": "Cannot proceed with task",
    "MAJOR": "Significant capability gap",
    "MINOR": "Minor features unavailable",
    "ADVISORY": "No functional impact",
}

# =============================================================================
# Known Incompatible Skill Combinations (SKILL.md Phase 2)
# =============================================================================

INCOMPATIBLE_COMBINATIONS = [
    ("canvas-design", "pdf"),  # Use pdf first to extract content
    ("frontend-design", "web-artifacts-builder"),  # Use isolated component trees
]

# =============================================================================
# Dependency Types (SKILL.md Phase 5)
# =============================================================================

DEPENDENCY_TYPES = {
    "DATA": {"symbol": "--data-->", "parallel": False},
    "CONTROL": {"symbol": "--ctrl-->", "parallel": False},
    "RESOURCE": {"symbol": "════", "parallel": "shared"},  # Only parallel if shared/locked
    "CONDITIONAL": {"symbol": "--if-->", "parallel": "conditional"},
    "OPTIONAL": {"symbol": "--?-->", "parallel": True},
}

# =============================================================================
# Preference Learning (SKILL.md Phase 6)
# =============================================================================

PREFERENCE_SIGNALS = {
    "vote": {"weight": 1.0, "description": "User explicitly chooses a skill"},
    "selection": {"weight": 0.8, "description": "User picks from offered options"},
    "usage": {"weight": 0.5, "description": "User completes task with skill"},
    "skip": {"weight": -0.3, "description": "User skips alternative"},
    "completion": {"weight": 0.3, "description": "Task completed successfully"},
}

PREFERENCE_HALFLIFE_DAYS = 30
PREFERENCE_EXPIRY_CONFIDENCE = 0.1
PREFERENCE_RECENT_DAYS = 7
PREFERENCE_RECENT_BOOST = 0.1

# =============================================================================
# Cost Estimation (SKILL.md Phase 9)
# =============================================================================

COST_CATEGORIES = ["token", "time", "external_api", "filesystem"]

COST_PRECISION = {
    "PRECISE": {"min_confidence": 90, "accuracy": 0.10},
    "FORECAST": {"min_confidence": 70, "accuracy": 0.30},
    "ESTIMATE": {"min_confidence": 50, "accuracy": 0.50},
}

DEFAULT_COST_LIMITS = {
    "token": {"warning": 50000, "critical": 100000},
    "time": {"warning": 300, "critical": 600},  # seconds
    "external_api": {"warning": 10, "critical": 50},
    "filesystem": {"warning": 100, "critical": 500},
}

# =============================================================================
# Version Tracking (SKILL.md Phase 10)
# =============================================================================

VERSION_SOURCES = {
    "metadata_version": {"priority": 1, "path": "SKILL.md frontmatter"},
    "frontmatter_version": {"priority": 2, "path": "SKILL.md frontmatter"},
    "directory_name": {"priority": 3, "path": "skill-name/v1.2.3/"},
    "git_tag": {"priority": 4, "path": ".git/refs/tags/"},
}

BREAKING_CHANGE_SEVERITY = {
    "CRITICAL": {"icon": "🔴", "impact": "Complete failure, data loss risk"},
    "MAJOR": {"icon": "🟠", "impact": "Significant feature loss, workflow broken"},
    "MINOR": {"icon": "🟡", "impact": "Minor features degraded, workarounds exist"},
    "ADVISORY": {"icon": "🔵", "impact": "No functional impact, cosmetic/performance"},
}

# =============================================================================
# Failure Handling Modes (SKILL.md Phase 5)
# =============================================================================

FAILURE_MODES = {
    "FAIL_FAST": "Stop on first failure, rollback changes",
    "FAIL_SOFT": "Try alternatives, skip if none available",
    "CONTINUE": "Execute all steps, report at end",
}

# =============================================================================
# Retry Configuration (SKILL.md Phase 5)
# =============================================================================

DEFAULT_RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay_ms": 1000,
    "max_delay_ms": 10000,
    "backoff_multiplier": 2.0,
}

# =============================================================================
# Skill Installation Sources (SKILL.md Phase 7)
# =============================================================================

INSTALL_SOURCES = [
    {"priority": 1, "name": "Built-in skills", "path": "~/.claude/skills/"},
    {"priority": 2, "name": "GitHub: anthropics/skills", "url": "https://github.com/anthropics/skills"},
    {"priority": 3, "name": "GitHub: other repos", "url": "user-specified"},
    {"priority": 4, "name": "Custom build", "tool": "skill-creator"},
]

# =============================================================================
# MCP Server Discovery Priorities (SKILL.md Phase 1)
# =============================================================================

MCP_DISCOVERY_PRIORITIES = [
    {"priority": 1, "source": "Global MCP", "path": "~/.claude/mcp.json"},
    {"priority": 2, "source": "Project MCP", "path": ".claude/mcp.json"},
    {"priority": 3, "source": "Settings", "path": "~/.claude/settings.json", "field": "mcpServers"},
    {"priority": 4, "source": "Plugins", "path": "~/.claude/plugins/*/settings.json"},
]

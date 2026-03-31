"""
Capability-to-Skill Mapping Table.
Extends the static table in SKILL.md into a runtime structure.
"""

from __future__ import annotations
from typing import Optional
from .models import SkillInfo, SkillMatch, Capability, MatchType, GapSeverity


# =============================================================================
# Capability Mapping Table (from SKILL.md Reference: Capability-to-Skill Mapping)
# =============================================================================

CAPABILITY_MAP: dict[str, dict] = {
    # PDF related
    "pdf": {
        "primary": "pdf",
        "alternative": "docx",
        "keywords": ["pdf", "extract text", "merge pdf", "ocr", "watermark", "text extraction"],
        "description": "PDF processing and manipulation",
    },
    # Spreadsheet / Excel
    "spreadsheet": {
        "primary": "xlsx",
        "alternative": "canvas-design",
        "keywords": ["spreadsheet", "excel", "data analysis", "chart", "csv", "xlsx", "xls"],
        "description": "Spreadsheet and data analysis",
    },
    # Presentation
    "presentation": {
        "primary": "pptx",
        "alternative": "canvas-design",
        "keywords": ["presentation", "slides", "deck", "powerpoint", "pptx", "ppt"],
        "description": "Presentation generation",
    },
    # Word document
    "word": {
        "primary": "docx",
        "alternative": "doc-coauthoring",
        "keywords": ["word", "docx", "letter", "report", "formal document", "document"],
        "description": "Word document creation and editing",
    },
    # Frontend / Website
    "frontend": {
        "primary": "frontend-design",
        "alternative": "web-artifacts-builder",
        "keywords": ["website", "web page", "ui", "react", "html", "css", "dashboard", "web"],
        "description": "Frontend web development",
    },
    # API / SDK
    "api": {
        "primary": "claude-api",
        "alternative": "mcp-builder",
        "keywords": ["api", "sdk", "claude integration", "llm app", "api integration"],
        "description": "API and SDK development",
    },
    # Documentation
    "documentation": {
        "primary": "doc-coauthoring",
        "alternative": "docx",
        "keywords": ["documentation", "proposal", "spec", "technical writing", "docs"],
        "description": "Technical documentation and proposals",
    },
    # Internal communications
    "internal-comms": {
        "primary": "internal-comms",
        "alternative": "docx",
        "keywords": ["internal comms", "announcement", "newsletter", "update", "internal"],
        "description": "Internal communications",
    },
    # MCP Server
    "mcp": {
        "primary": "mcp-builder",
        "alternative": None,
        "keywords": ["mcp server", "model context protocol", "tool integration", "mcp"],
        "description": "MCP server development",
    },
    # Algorithmic art
    "algorithmic-art": {
        "primary": "algorithmic-art",
        "alternative": "canvas-design",
        "keywords": ["generative art", "algorithmic", "p5.js", "flow field", "art", "generative"],
        "description": "Algorithmic and generative art",
    },
    # Visual design
    "visual-design": {
        "primary": "canvas-design",
        "alternative": "pptx",
        "keywords": ["poster", "visual art", "flyer", "png", "pdf design", "design", "visual"],
        "description": "Visual design and graphics",
    },
    # GIF
    "gif": {
        "primary": "slack-gif-creator",
        "alternative": "algorithmic-art",
        "keywords": ["gif", "slack animation", "animated gif"],
        "description": "GIF creation for Slack",
    },
    # Theme
    "theme": {
        "primary": "theme-factory",
        "alternative": "brand-guidelines",
        "keywords": ["theme", "styling", "consistent look", "theme factory"],
        "description": "Theme creation and styling",
    },
    # Brand
    "brand": {
        "primary": "brand-guidelines",
        "alternative": "theme-factory",
        "keywords": ["brand colors", "anthropic style", "brand", "style guidelines"],
        "description": "Brand guidelines application",
    },
    # React artifact
    "react-artifact": {
        "primary": "web-artifacts-builder",
        "alternative": "frontend-design",
        "keywords": ["react artifact", "complex ui", "shadcn", "react component"],
        "description": "Complex React artifact building",
    },
    # Testing
    "testing": {
        "primary": "webapp-testing",
        "alternative": "web-access",
        "keywords": ["testing", "playwright", "screenshot", "browser", "test"],
        "description": "Web application testing",
    },
    # Web access
    "web-access": {
        "primary": "web-access",
        "alternative": None,
        "keywords": ["web search", "scraping", "browser", "login-required", "crawl", "scrape"],
        "description": "Web access and scraping",
    },
    # Skill creation
    "skill-creation": {
        "primary": "skill-creator",
        "alternative": None,
        "keywords": ["skill creation", "eval", "benchmark", "create skill"],
        "description": "Skill creation and evaluation",
    },
}

# =============================================================================
# MCP Capability Keywords (from SKILL.md Phase 1.3)
# =============================================================================

MCP_CAPABILITY_KEYWORDS: dict[str, set[str]] = {
    "file": {"read", "write", "delete", "copy", "move", "exists", "stat", "glob"},
    "http": {"fetch", "request", "get", "post", "put", "delete", "api"},
    "database": {"query", "execute", "select", "insert", "update", "delete", "db"},
    "shell": {"bash", "shell", "exec", "command", "run", "script"},
    "git": {"commit", "push", "pull", "branch", "checkout", "clone", "git"},
    "browser": {"click", "type", "screenshot", "navigate", "evaluate", "dom"},
    "search": {"search", "find", "query", "grep", "match"},
    "memory": {"remember", "recall", "store", "get", "search"},
}

# =============================================================================
# Skill to Capability Reverse Mapping
# =============================================================================

SKILL_TO_CAPABILITIES: dict[str, list[str]] = {}
for cap, info in CAPABILITY_MAP.items():
    primary = info["primary"]
    if primary not in SKILL_TO_CAPABILITIES:
        SKILL_TO_CAPABILITIES[primary] = []
    SKILL_TO_CAPABILITIES[primary].append(cap)
    if info["alternative"]:
        alt = info["alternative"]
        if alt not in SKILL_TO_CAPABILITIES:
            SKILL_TO_CAPABILITIES[alt] = []
        SKILL_TO_CAPABILITIES[alt].append(cap)

# =============================================================================
# Action verbs for capability inference
# =============================================================================

ACTION_VERBS: dict[str, list[str]] = {
    "extract": ["extract", "parse", "read", "get", "fetch", "retrieve", "scrape"],
    "generate": ["generate", "create", "make", "produce", "build", "write"],
    "transform": ["transform", "convert", "parse", "process", "format", "convert"],
    "analyze": ["analyze", "examine", "review", "assess", "evaluate", "calculate"],
    "visualize": ["visualize", "chart", "plot", "graph", "display", "render"],
    "present": ["present", "display", "show", "summarize", "report"],
    "test": ["test", "verify", "check", "validate", "screenshot"],
    "crawl": ["crawl", "scrape", "browse", "navigate", "access"],
    "design": ["design", "create", "layout", "style", "theme"],
    "integrate": ["integrate", "connect", "link", "combine", "merge"],
}

# =============================================================================
# Functions
# =============================================================================


def find_skill_for_capability(
    capability: str,
    available_skills: list[str],
    mcp_tools: list[str] | None = None
) -> SkillMatch:
    """
    Find the best matching skill for a given capability.

    Args:
        capability: The capability name (e.g., "pdf", "spreadsheet")
        available_skills: List of installed skill names
        mcp_tools: Optional list of available MCP tool names

    Returns:
        SkillMatch with primary skill, alternative, and match type
    """
    capability_lower = capability.lower()

    # Direct match in capability map
    if capability_lower in CAPABILITY_MAP:
        mapping = CAPABILITY_MAP[capability_lower]
        primary_name = mapping["primary"]
        alt_name = mapping.get("alternative")

        # Find primary skill
        primary_skill = None
        if primary_name in available_skills:
            primary_skill = SkillInfo(name=primary_name)

        # Find alternative skill
        alt_skill = None
        if alt_name and alt_name in available_skills:
            alt_skill = SkillInfo(name=alt_name)

        if primary_skill:
            return SkillMatch(
                capability=Capability(name=capability, action=""),
                skill=primary_skill,
                match_type=MatchType.EXACT if primary_name == capability_lower else MatchType.PRIMARY,
                alternative=alt_skill,
            )

    # Keyword matching - search through capabilities
    for cap_key, mapping in CAPABILITY_MAP.items():
        if cap_key in available_skills:
            for kw in mapping.get("keywords", []):
                if kw.lower() in capability_lower or capability_lower in kw.lower():
                    return SkillMatch(
                        capability=Capability(name=capability, action=""),
                        skill=SkillInfo(name=cap_key),
                        match_type=MatchType.PARTIAL,
                        alternative=SkillInfo(name=mapping["alternative"]) if mapping.get("alternative") else None,
                    )

    # Check MCP tools as fallback
    if mcp_tools:
        for tool in mcp_tools:
            tool_lower = tool.lower()
            for mcp_cap, keywords in MCP_CAPABILITY_KEYWORDS.items():
                if any(kw in tool_lower for kw in keywords):
                    return SkillMatch(
                        capability=Capability(name=capability, action=""),
                        skill=SkillInfo(name=tool, capabilities=[mcp_cap]),
                        match_type=MatchType.INFERRED,
                    )

    # No match found
    return SkillMatch(
        capability=Capability(name=capability, action=""),
        skill=None,
        match_type=MatchType.MISSING,
    )


def infer_capability_from_action(
    action: str,
    target: str,
    available_skills: list[str]
) -> list[str]:
    """
    Infer capabilities from an action + target combination.

    Example:
        action="extract", target="tables from PDF"
        -> ["pdf"]
    """
    inferred = []
    action_lower = action.lower()
    target_lower = target.lower()

    # Match action verbs to capabilities
    for cap_action, verbs in ACTION_VERBS.items():
        if any(verb in action_lower for verb in verbs):
            # Find capability that matches this action
            for cap, mapping in CAPABILITY_MAP.items():
                cap_action_lower = cap_action.lower()
                if (cap_action_lower in target_lower or
                    any(verb in target_lower for verb in mapping.get("keywords", []))):
                    if mapping["primary"] in available_skills:
                        inferred.append(cap)

    return list(set(inferred))


def get_capability_keywords(capability: str) -> list[str]:
    """Get all keywords for a capability."""
    if capability.lower() in CAPABILITY_MAP:
        return CAPABILITY_MAP[capability.lower()].get("keywords", [])
    return []


def get_skill_description(skill_name: str) -> str:
    """Get the description for a skill."""
    for cap, mapping in CAPABILITY_MAP.items():
        if mapping["primary"] == skill_name:
            return mapping.get("description", "")
        if mapping.get("alternative") == skill_name:
            return mapping.get("description", "")
    return ""


def list_all_capabilities() -> list[str]:
    """List all known capabilities."""
    return list(CAPABILITY_MAP.keys())


def is_skill_incompatible(skill_a: str, skill_b: str) -> bool:
    """Check if two skills are known to be incompatible."""
    from .config import INCOMPATIBLE_COMBINATIONS
    pair = tuple(sorted([skill_a, skill_b]))
    return pair in INCOMPATIBLE_COMBINATIONS

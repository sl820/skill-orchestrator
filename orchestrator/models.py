"""
Core data models for Skill Orchestrator.
All modules depend on these classes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime


class ExecutionMode(Enum):
    """Execution modes based on risk and user preference."""
    AUTO = "AUTO"       # Execute immediately after heads-up
    SUGGEST = "SUGGEST" # Show plan, wait for confirmation
    PLAN = "PLAN"       # Show detailed plan, wait for approval
    THINK = "THINK"     # Show reasoning, don't execute until asked
    ADAPTIVE = "ADAPTIVE"  # Re-plan dynamically on failures


class FailureMode(Enum):
    """Failure handling strategies."""
    FAIL_FAST = "FAIL_FAST"     # Stop on first failure, rollback
    FAIL_SOFT = "FAIL_SOFT"    # Try alternatives, skip if none
    CONTINUE = "CONTINUE"       # Execute all, report at end


class ConfidenceLevel(Enum):
    """Confidence level thresholds."""
    EXCELLENT = "EXCELLENT"  # 90-100%
    GOOD = "GOOD"            # 70-89%
    MODERATE = "MODERATE"    # 50-69%
    WEAK = "WEAK"            # 30-49%
    POOR = "POOR"            # 0-29%


class RiskLevel(Enum):
    """Risk level for operations."""
    LOW = "LOW"        # 0.2 - Read-only, reversible
    MEDIUM = "MEDIUM"  # 0.5 - Minor side effects
    HIGH = "HIGH"      # 0.75 - Significant changes
    CRITICAL = "CRITICAL"  # 1.0 - Irreversible


class DependencyType(Enum):
    """Types of dependencies between execution steps."""
    DATA = "DATA"              # A's output is B's input
    CONTROL = "CONTROL"       # B waits for A to complete
    RESOURCE = "RESOURCE"      # Both need same resource
    CONDITIONAL = "CONDITIONAL" # B runs only if A meets condition
    OPTIONAL = "OPTIONAL"      # B can run independently


class MatchType(Enum):
    """Skill matching types."""
    EXACT = "EXACT"       # Direct capability match
    PRIMARY = "PRIMARY"   # Primary skill for this capability
    PARTIAL = "PARTIAL"   # Partial overlap
    INFERRED = "INFERRED" # Inferred from context
    MISSING = "MISSING"   # No skill available


class GapSeverity(Enum):
    """Severity of capability gaps."""
    BLOCKING = "BLOCKING"  # Cannot proceed
    MAJOR = "MAJOR"        # Significant gap
    MINOR = "MINOR"        # Minor features unavailable
    ADVISORY = "ADVISORY"  # No functional impact


@dataclass
class InputSpec:
    """Specification for a task input."""
    type: str                    # e.g., "file", "text", "url"
    path: Optional[str] = None  # File path or URL
    description: str = ""
    required: bool = True
    format: Optional[str] = None  # e.g., "json", "csv", "pdf"


@dataclass
class OutputSpec:
    """Specification for a task output."""
    type: str                     # e.g., "file", "text", "artifact"
    path: Optional[str] = None    # Expected output path
    description: str = ""
    format: Optional[str] = None  # e.g., "pdf", "png", "docx"


@dataclass
class Capability:
    """A capability required by a task."""
    name: str                     # e.g., "pdf", "spreadsheet", "presentation"
    action: str                   # e.g., "extract", "generate", "transform"
    constraints: dict = field(default_factory=dict)
    match_type: MatchType = MatchType.MISSING
    severity: GapSeverity = GapSeverity.ADVISORY

    def __str__(self) -> str:
        return f"{self.name}:{self.action}"


@dataclass
class SkillInfo:
    """Information about an installed skill."""
    name: str
    version: str = "unknown"
    version_source: str = "none"
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    has_eval: bool = False
    path: str = ""
    capabilities: list[str] = field(default_factory=list)


@dataclass
class SkillMatch:
    """Result of matching a capability to a skill."""
    capability: Capability
    skill: Optional[SkillInfo]
    confidence: float = 0.0        # 0.0-1.0
    match_type: MatchType = MatchType.MISSING
    alternative: Optional[SkillInfo] = None
    confidence_breakdown: dict = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.skill is not None and self.match_type != MatchType.MISSING

    @property
    def confidence_level(self) -> ConfidenceLevel:
        pct = self.confidence * 100
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


@dataclass
class StepDependency:
    """A dependency between execution steps."""
    from_step: str
    to_step: str
    dep_type: DependencyType
    description: str = ""


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    skill: str
    action: str
    status: str = "pending"     # pending, running, done, failed, skipped
    success: bool = False
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    fallback_used: bool = False

    @property
    def duration_ms(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    step_id: str
    skill: str
    action: str
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # step_ids this depends on
    depends_on: list[StepDependency] = field(default_factory=list)
    status: str = "pending"
    result: Optional[StepResult] = None
    retry_policy: dict = field(default_factory=dict)
    rollback_on: Optional[str] = None
    warning: Optional[str] = None

    def __str__(self) -> str:
        return f"[{self.step_id}] {self.skill}:{self.action}"


@dataclass
class RiskAssessment:
    """Result of risk assessment for a task."""
    overall_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    dimensions: dict = field(default_factory=dict)
    reversibility_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ConflictResolution:
    """Result of conflict resolution between skills."""
    skill_a: SkillMatch
    skill_b: SkillMatch
    score_a: float
    score_b: float
    gap: float
    mode: str = "MANUAL"  # AUTO, HYBRID, MANUAL
    recommended: Optional[str] = None
    options: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Complete execution plan for a task."""
    task: Task
    mode: ExecutionMode
    steps: list[ExecutionStep] = field(default_factory=list)
    skill_matches: list[SkillMatch] = field(default_factory=list)
    gaps: list[SkillMatch] = field(default_factory=list)
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    conflicts: list[ConflictResolution] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)  # Steps that can run in parallel
    estimated_duration_ms: Optional[float] = None
    estimated_cost: dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of executing a complete plan."""
    plan: ExecutionPlan
    step_results: list[StepResult] = field(default_factory=list)
    success: bool = False
    total_duration_ms: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: list[str] = field(default_factory=list)
    partial_results: dict = field(default_factory=dict)

    @property
    def completed_steps(self) -> int:
        return sum(1 for r in self.step_results if r.status == "done")

    @property
    def failed_steps(self) -> int:
        return sum(1 for r in self.step_results if r.status == "failed")


@dataclass
class Task:
    """A user task to be orchestrated."""
    goal: str
    original_request: str
    inputs: list[InputSpec] = field(default_factory=list)
    outputs: list[OutputSpec] = field(default_factory=list)
    capabilities_needed: list[Capability] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Task: {self.goal}"


@dataclass
class CostEstimate:
    """Estimated cost for a task or step."""
    token_estimate: int = 0
    time_estimate_seconds: float = 0.0
    external_api_calls: int = 0
    filesystem_ops: int = 0
    precision: str = "ESTIMATE"  # PRECISE, FORECAST, ESTIMATE
    confidence: float = 0.5
    breakdown: dict = field(default_factory=dict)


@dataclass
class VersionInfo:
    """Version information for a skill."""
    skill_name: str
    installed_version: str = "unknown"
    latest_version: Optional[str] = None
    source: str = "none"
    update_available: bool = False
    update_type: Optional[str] = None  # PATCH, MINOR, MAJOR
    changelog: list[str] = field(default_factory=list)


@dataclass
class CompatibilityInfo:
    """Compatibility information for a skill."""
    skill_name: str
    version: str
    compatible: bool = True
    issues: list[str] = field(default_factory=list)
    claude_code_version: Optional[str] = None
    nodejs_version: Optional[str] = None
    platform: Optional[str] = None
    dependencies: dict = field(default_factory=dict)
    verified_combinations: list[dict] = field(default_factory=list)


@dataclass
class BreakingChange:
    """A breaking change between skill versions."""
    severity: str
    description: str
    previous_behavior: Optional[str] = None
    new_behavior: Optional[str] = None
    impact: str = ""
    mitigation: Optional[str] = None


@dataclass
class UserPreference:
    """A learned user preference for a skill."""
    skill: str
    capability: str
    preference: float = 0.0    # -1.0 to +1.0
    confidence: float = 0.0    # 0.0 to 1.0
    source: str = "implicit"   # explicit, implicit, combined
    evidence: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_strong(self) -> bool:
        return abs(self.preference) >= 0.6 and self.confidence >= 0.7

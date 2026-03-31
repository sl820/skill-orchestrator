"""
User Preference Learning System.
Learns and persists user preferences for skill selection.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .models import UserPreference


class PreferenceStore:
    """
    Persistent store for user preferences.

    Tracks explicit and implicit user preferences for skill selection
    and task execution patterns.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize preference store.

        Args:
            storage_path: Path to persist preferences (optional)
        """
        self.storage_path = storage_path
        self.preferences: dict[str, UserPreference] = {}
        self._load()

    def add_explicit_preference(
        self,
        skill: str,
        capability: str,
        preference: float
    ) -> UserPreference:
        """
        Record an explicit user preference (direct choice).

        Args:
            skill: Skill name
            capability: Capability name
            preference: -1.0 (strongly dislike) to +1.0 (strongly prefer)

        Returns:
            Created or updated UserPreference
        """
        key = f"{capability}:{skill}"
        now = datetime.now()

        if key in self.preferences:
            pref = self.preferences[key]
            pref.preference = preference
            pref.confidence = 1.0  # Explicit preferences are high confidence
            pref.source = "explicit"
            pref.updated_at = now
        else:
            pref = UserPreference(
                skill=skill,
                capability=capability,
                preference=preference,
                confidence=1.0,
                source="explicit",
                created_at=now,
                updated_at=now
            )
            self.preferences[key] = pref

        self._save()
        return pref

    def add_implicit_preference(
        self,
        skill: str,
        capability: str,
        success: bool,
        context: Optional[dict] = None
    ) -> UserPreference:
        """
        Record an implicit preference (observed from behavior).

        Args:
            skill: Skill name
            capability: Capability name
            success: Whether the execution was successful
            context: Additional context about the execution

        Returns:
            Created or updated UserPreference
        """
        key = f"{capability}:{skill}"
        now = datetime.now()

        # Success increases preference, failure decreases
        delta = 0.1 if success else -0.15

        if key in self.preferences:
            pref = self.preferences[key]
            # Update with exponential moving average
            pref.preference = max(-1.0, min(1.0, pref.preference * 0.9 + delta * 0.1))
            pref.confidence = min(1.0, pref.confidence + 0.05)
            pref.source = "implicit"
            pref.updated_at = now

            if context:
                pref.evidence.append({
                    "timestamp": now.isoformat(),
                    "success": success,
                    "context": context
                })
        else:
            initial = delta
            pref = UserPreference(
                skill=skill,
                capability=capability,
                preference=initial,
                confidence=0.3,
                source="implicit",
                evidence=[{
                    "timestamp": now.isoformat(),
                    "success": success,
                    "context": context or {}
                }],
                created_at=now,
                updated_at=now
            )
            self.preferences[key] = pref

        self._save()
        return pref

    def get_preference(self, skill: str, capability: str) -> Optional[UserPreference]:
        """Get preference for a skill/capability pair."""
        key = f"{capability}:{skill}"
        return self.preferences.get(key)

    def get_skill_preference(self, skill: str) -> list[UserPreference]:
        """Get all preferences for a skill across capabilities."""
        return [p for p in self.preferences.values() if p.skill == skill]

    def get_capability_preference(self, capability: str) -> list[UserPreference]:
        """Get all preferences for a capability across skills."""
        return [p for p in self.preferences.values() if p.capability == capability]

    def is_skill_preferred(self, skill: str, capability: str) -> bool:
        """Check if a skill is preferred for a capability."""
        pref = self.get_preference(skill, capability)
        return pref is not None and pref.preference > 0 and pref.is_strong

    def get_preferred_skill(self, capability: str) -> Optional[str]:
        """Get the most preferred skill for a capability."""
        prefs = self.get_capability_preference(capability)
        strong_prefs = [p for p in prefs if p.is_strong]
        if strong_prefs:
            return max(strong_prefs, key=lambda p: p.preference).skill
        return None

    def remove_preference(self, skill: str, capability: str) -> bool:
        """Remove a preference."""
        key = f"{capability}:{skill}"
        if key in self.preferences:
            del self.preferences[key]
            self._save()
            return True
        return False

    def clear_all(self) -> None:
        """Clear all preferences."""
        self.preferences.clear()
        self._save()

    def get_statistics(self) -> dict:
        """Get preference store statistics."""
        strong = sum(1 for p in self.preferences.values() if p.is_strong)
        explicit = sum(1 for p in self.preferences.values() if p.source == "explicit")
        return {
            "total_preferences": len(self.preferences),
            "strong_preferences": strong,
            "explicit_preferences": explicit,
            "implicit_preferences": len(self.preferences) - explicit,
        }

    def _load(self) -> None:
        """Load preferences from storage."""
        if not self.storage_path:
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            self.preferences = {}
            for key, item in data.items():
                pref = UserPreference(
                    skill=item["skill"],
                    capability=item["capability"],
                    preference=item["preference"],
                    confidence=item.get("confidence", 0.5),
                    source=item.get("source", "implicit"),
                    evidence=item.get("evidence", []),
                    created_at=datetime.fromisoformat(item.get("created_at", datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(item.get("updated_at", datetime.now().isoformat()))
                )
                self.preferences[key] = pref
        except Exception:
            pass  # Start with empty store if load fails

    def _save(self) -> None:
        """Save preferences to storage."""
        if not self.storage_path:
            return

        try:
            data = {}
            for key, pref in self.preferences.items():
                data[key] = {
                    "skill": pref.skill,
                    "capability": pref.capability,
                    "preference": pref.preference,
                    "confidence": pref.confidence,
                    "source": pref.source,
                    "evidence": pref.evidence,
                    "created_at": pref.created_at.isoformat(),
                    "updated_at": pref.updated_at.isoformat()
                }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Silently fail if save fails


def format_preference_display(pref: UserPreference) -> str:
    """Format a user preference as human-readable string."""
    strength = "strong" if pref.is_strong else "moderate"
    direction = "prefer" if pref.preference > 0 else "avoid"

    lines = [
        f"Preference: {pref.skill} for {pref.capability}",
        f"  Strength: {strength} ({pref.confidence:.0%} confidence)",
        f"  Direction: {direction} ({pref.preference:+.2f})",
        f"  Source: {pref.source}",
        f"  Evidence: {len(pref.evidence)} observations"
    ]

    return "\n".join(lines)

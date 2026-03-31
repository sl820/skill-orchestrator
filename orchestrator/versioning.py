"""
Skill Version Tracking.
Tracks and manages skill versions with compatibility checking.
"""

from __future__ import annotations
import re
import os
from dataclasses import dataclass
from typing import Optional
from .models import VersionInfo, CompatibilityInfo, BreakingChange

# Pre-compiled regex patterns for version parsing
FRONTMATTER_METADATA_VERSION_RE = re.compile(r'metadata:\s*\n\s*version:\s*["\']?([^"\'\n]+)["\']?')
FRONTMATTER_VERSION_RE = re.compile(r'^version:\s*["\']?([^"\'\n]+)["\']?', re.MULTILINE)
DIRECTORY_VERSION_RE = re.compile(r'-(\d+\.\d+\.\d+)$')
PARSE_VERSION_RE = re.compile(r'(\d+)\.?(\d+)?\.?(\d+)?')


class VersionTracker:
    """
    Tracks skill versions and checks for updates.

    Supports multiple version sources:
    1. metadata.version in SKILL.md frontmatter
    2. frontmatter.version field
    3. Directory name (skills/<name>-<version>)
    4. Git tag (skills/<name>/v<version>)
    """

    def __init__(self, skills_base_path: str = "skills"):
        """
        Initialize version tracker.

        Args:
            skills_base_path: Base path to skills directory
        """
        self.skills_base_path = skills_base_path
        self.version_cache: dict[str, VersionInfo] = {}

    def get_version_info(self, skill_name: str) -> VersionInfo:
        """
        Get complete version information for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            VersionInfo with all version details
        """
        # Check cache first
        if skill_name in self.version_cache:
            return self.version_cache[skill_name]

        # Try each source in priority order
        version = "unknown"
        source = "none"

        # 1. Try metadata.version in frontmatter
        version, source = self._read_frontmatter_version(skill_name)
        if version != "unknown":
            return self._build_version_info(skill_name, version, source)

        # 2. Try frontmatter version field
        version, source = self._read_frontmatter_version_field(skill_name)
        if version != "unknown":
            return self._build_version_info(skill_name, version, source)

        # 3. Try directory name
        version, source = self._read_directory_version(skill_name)
        if version != "unknown":
            return self._build_version_info(skill_name, version, source)

        # 4. Try git tag
        version, source = self._read_git_tag_version(skill_name)
        if version != "unknown":
            return self._build_version_info(skill_name, version, source)

        # No version found
        info = VersionInfo(skill_name=skill_name, source="none")
        self.version_cache[skill_name] = info
        return info

    def _read_frontmatter_version(self, skill_name: str) -> tuple[str, str]:
        """Try to read metadata.version from SKILL.md frontmatter."""
        skill_path = os.path.join(self.skills_base_path, skill_name, "SKILL.md")
        if not os.path.exists(skill_path):
            return "unknown", "none"

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for metadata.version
            match = FRONTMATTER_METADATA_VERSION_RE.search(content)
            if match:
                return match.group(1).strip(), "metadata.version"
        except Exception:
            pass

        return "unknown", "none"

    def _read_frontmatter_version_field(self, skill_name: str) -> tuple[str, str]:
        """Try to read version directly from frontmatter."""
        skill_path = os.path.join(self.skills_base_path, skill_name, "SKILL.md")
        if not os.path.exists(skill_path):
            return "unknown", "none"

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for version: in frontmatter (non-metadata context)
            match = FRONTMATTER_VERSION_RE.search(content)
            if match:
                return match.group(1).strip(), "frontmatter"
        except Exception:
            pass

        return "unknown", "none"

    def _read_directory_version(self, skill_name: str) -> tuple[str, str]:
        """Try to read version from directory name."""
        skill_path = os.path.join(self.skills_base_path, skill_name)
        if not os.path.exists(skill_path):
            return "unknown", "none"

        # Directory name patterns: skill-name-v1.0.0, skill-name-1.0.0
        dirname = os.path.basename(skill_path)
        match = DIRECTORY_VERSION_RE.search(dirname)
        if match:
            return match.group(1), "directory"

        return "unknown", "none"

    def _read_git_tag_version(self, skill_name: str) -> tuple[str, str]:
        """Try to read version from git tag."""
        import subprocess
        import os

        skill_path = os.path.join(self.skills_base_path, skill_name)
        if not os.path.exists(skill_path):
            return "unknown", "none"

        try:
            # Check for git tag like v1.0.0 or 1.0.0
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                # Remove 'v' prefix if present
                if tag.startswith('v'):
                    return tag[1:], "git_tag"
                return tag, "git_tag"
        except Exception:
            pass

        return "unknown", "none"

    def _build_version_info(
        self,
        skill_name: str,
        version: str,
        source: str
    ) -> VersionInfo:
        """Build a complete VersionInfo object."""
        info = VersionInfo(
            skill_name=skill_name,
            installed_version=version,
            source=source,
            update_available=False
        )
        self.version_cache[skill_name] = info
        return info

    def check_for_updates(self, skill_name: str) -> VersionInfo:
        """
        Check if a skill has updates available.

        Args:
            skill_name: Name of the skill

        Returns:
            Updated VersionInfo with update information
        """
        info = self.get_version_info(skill_name)

        # In a real implementation, would compare against registry
        # For now, just return current info
        return info

    def get_compatibility_info(
        self,
        skill_name: str,
        version: str,
        platform: Optional[str] = None
    ) -> CompatibilityInfo:
        """
        Get compatibility information for a skill version.

        Args:
            skill_name: Name of the skill
            version: Version to check
            platform: Optional platform specifier

        Returns:
            CompatibilityInfo with compatibility details
        """
        # In a real implementation, would check against known compatible versions
        # For now, return placeholder
        return CompatibilityInfo(
            skill_name=skill_name,
            version=version,
            compatible=True,
            platform=platform
        )


def parse_version(version_str: str) -> tuple[int, int, int]:
    """
    Parse version string into components.

    Args:
        version_str: Version string like "1.2.3"

    Returns:
        Tuple of (major, minor, patch)
    """
    # Remove 'v' prefix
    version_str = version_str.lstrip('v')

    # Extract numeric parts
    match = PARSE_VERSION_RE.match(version_str)
    if match:
        major = int(match.group(1)) if match.group(1) else 0
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)

    return (0, 0, 0)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Args:
        v1: First version
        v2: Second version

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    parsed_v1 = parse_version(v1)
    parsed_v2 = parse_version(v2)

    if parsed_v1 < parsed_v2:
        return -1
    elif parsed_v1 > parsed_v2:
        return 1
    return 0


def get_update_type(current: str, latest: str) -> Optional[str]:
    """
    Determine the type of update between versions.

    Args:
        current: Current version
        latest: Latest available version

    Returns:
        "MAJOR", "MINOR", "PATCH", or None if no update
    """
    cur = parse_version(current)
    lat = parse_version(latest)

    if lat[0] > cur[0]:
        return "MAJOR"
    elif lat[1] > cur[1]:
        return "MINOR"
    elif lat[2] > cur[2]:
        return "PATCH"
    return None


def detect_breaking_changes(
    current: str,
    latest: str,
    changelog: list[str]
) -> list[BreakingChange]:
    """
    Detect breaking changes between versions.

    Args:
        current: Current version
        latest: Latest version
        changelog: Changelog entries

    Returns:
        List of BreakingChange objects
    """
    changes = []
    current_parts = parse_version(current)
    latest_parts = parse_version(latest)

    # Major version bump indicates breaking changes
    if latest_parts[0] > current_parts[0]:
        changes.append(BreakingChange(
            severity="MAJOR",
            description="Major version increment indicates breaking changes",
            impact="API or behavior changes that may require code updates"
        ))

    # Look for BREAKING in changelog
    for entry in changelog:
        if "BREAKING" in entry.upper():
            changes.append(BreakingChange(
                severity="MINOR",
                description=entry,
                impact="See changelog for details"
            ))

    return changes


def format_version_info(info: VersionInfo) -> str:
    """Format version info as human-readable string."""
    lines = [
        f"Version Info for {info.skill_name}:",
        f"  Installed: {info.installed_version}",
        f"  Source: {info.source}"
    ]

    if info.latest_version:
        lines.append(f"  Latest: {info.latest_version}")
        if info.update_available:
            lines.append(f"  Update Type: {info.update_type}")
        else:
            lines.append("  Status: Up to date")

    if info.update_available and info.changelog:
        lines.append("  Changelog:")
        for entry in info.changelog[:5]:  # Show first 5 entries
            lines.append(f"    - {entry}")

    return "\n".join(lines)

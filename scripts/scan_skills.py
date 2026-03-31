#!/usr/bin/env python3
"""
Dynamic Skill Scanner for Skill Orchestrator
Scans ~/.claude/skills/ and builds a capability map.
Supports both Skills and MCP servers.
"""

import json
import re
from pathlib import Path

# Pre-compiled regex patterns for performance
_RE_FRONTMATTER = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
_RE_VERSION_DIR = re.compile(r'[_-]?v?(\d+\.\d+\.\d+)')
_RE_SEMVER_FULL = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([^+]+))?(?:\+(.+))?$')
_RE_SEMVER_PARTIAL = re.compile(r'^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$')
_RE_DESCRIPTION = re.compile(r'description:\s*>?\s*(.+?)(?:\n---|\n#)', re.DOTALL)
_RE_ACTION_WORDS = re.compile(r'\b(creating|building|designing|generating|manipulating|editing|crawling|scraping|testing|writing|formatting|applying|producing|making)\b')
_RE_SKILL_REFS = re.compile(r'`(\w+(?:-\w+)*)`')
_RE_DESC_WORDS = re.compile(r'\b\w{4,}\b')

# Constant: stopwords to exclude from capability map
_STOPWORDS = frozenset({
    'when', 'what', 'where', 'which', 'skill', 'skills', 'this', 'that',
    'these', 'those', 'with', 'from', 'have', 'been', 'being', 'their',
    'there', 'here', 'your', 'they',
})

# MCP capability keyword map (matches SKILL.md Phase 1.3)
_MCP_CAPABILITY_KEYWORDS = {
    'file': {'read', 'write', 'delete', 'copy', 'move', 'exists', 'stat', 'glob'},
    'http': {'fetch', 'request', 'get', 'post', 'put', 'delete', 'api'},
    'database': {'query', 'execute', 'select', 'insert', 'update', 'delete', 'db'},
    'shell': {'bash', 'shell', 'exec', 'command', 'run', 'script'},
    'git': {'commit', 'push', 'pull', 'branch', 'checkout', 'clone', 'git'},
    'browser': {'click', 'type', 'screenshot', 'navigate', 'evaluate', 'dom'},
    'search': {'search', 'find', 'query', 'grep', 'match'},
    'memory': {'remember', 'recall', 'store', 'get', 'search'},
}

# Try to import yaml at module level
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from SKILL.md content."""
    match = _RE_FRONTMATTER.match(content)
    if not match:
        return {}

    if _HAS_YAML:
        fm = yaml.safe_load(match.group(1))
        return fm if isinstance(fm, dict) else {}
    else:
        # Fallback: simple key: value parsing
        fm = {}
        for line in match.group(1).split('\n'):
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip().strip('"\'')
                if key == 'metadata' and value in ('', '|', '>'):
                    fm[key] = {}
                elif key and value:
                    fm[key] = value
        return fm


def extract_version(fm: dict, skill_name: str) -> dict:
    """Extract version information from frontmatter metadata."""
    version = None
    source = None

    # Priority 1: metadata.version
    metadata = fm.get('metadata', {})
    if isinstance(metadata, dict) and metadata.get('version'):
        version = metadata.get('version')
        source = 'metadata.version'

    # Priority 2: top-level version field
    if not version and fm.get('version'):
        version = fm.get('version')
        source = 'frontmatter.version'

    # Priority 3: directory name with version suffix
    if not version:
        match = _RE_VERSION_DIR.search(skill_name)
        if match:
            version = match.group(1)
            source = 'directory.name'

    return {
        "version": version or "unknown",
        "source": source or 'none',
        "semver": _parse_semver(version) if version else None,
    }


def _parse_semver(version_str: str) -> dict:
    """Parse a semantic version string into components."""
    if not version_str or version_str == 'unknown':
        return None
    match = _RE_SEMVER_FULL.match(version_str)
    if match:
        return {
            "major": int(match.group(1)),
            "minor": int(match.group(2)),
            "patch": int(match.group(3)),
            "prerelease": match.group(4),
            "build": match.group(5),
        }
    # Try partial semver (e.g., "2.4" or just "3")
    partial = _RE_SEMVER_PARTIAL.match(version_str)
    if partial:
        return {
            "major": int(partial.group(1)),
            "minor": int(partial.group(2)) if partial.group(2) else 0,
            "patch": int(partial.group(3)) if partial.group(3) else 0,
            "prerelease": None,
            "build": None,
        }
    return None


def extract_keywords(content: str) -> list:
    """Extract capability keywords from SKILL.md body."""
    keywords = set()

    # Extract description sentences
    desc_match = _RE_DESCRIPTION.search(content)
    if desc_match:
        desc = desc_match.group(1).lower()
        # Extract action verbs and nouns
        action_words = _RE_ACTION_WORDS.findall(desc)
        keywords.update(action_words)

    # Extract skill names referenced
    skill_refs = _RE_SKILL_REFS.findall(content)
    keywords.update(skill_refs)

    return sorted(keywords)


def scan_mcp_servers() -> dict:
    """Scan MCP server configurations from standard locations.

    Scans in priority order:
    1. Global MCP:    ~/.claude/mcp.json
    2. Project MCP:  .claude/mcp.json (cwd)
    3. Settings:      ~/.claude/settings.json  (mcpServers field)
    4. Plugins:       ~/.claude/plugins/*/settings.json
    """
    mcp_servers = []
    seen = set()  # deduplicate by server name

    # Helper to load JSON safely
    def load_json(path: Path) -> dict | None:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass
        return None

    home = Path.home()

    # Priority 1: ~/.claude/mcp.json
    global_mcp = home / '.claude' / 'mcp.json'
    data = load_json(global_mcp)
    if data:
        # mcp.json is an array of server configs
        servers = data if isinstance(data, list) else data.get('mcpServers', [])
        for s in servers:
            name = s.get('name') or s.get('server') or str(s)
            if name not in seen:
                seen.add(name)
                mcp_servers.append({'name': name, 'config': s, 'source': str(global_mcp)})

    # Priority 2: .claude/mcp.json (cwd)
    local_mcp = Path('.claude/mcp.json')
    data = load_json(local_mcp)
    if data:
        servers = data if isinstance(data, list) else data.get('mcpServers', [])
        for s in servers:
            name = s.get('name') or s.get('server') or str(s)
            if name not in seen:
                seen.add(name)
                mcp_servers.append({'name': name, 'config': s, 'source': str(local_mcp)})

    # Priority 3: ~/.claude/settings.json (mcpServers field)
    settings = load_json(home / '.claude' / 'settings.json')
    if settings and settings.get('mcpServers'):
        for name, cfg in settings['mcpServers'].items():
            if name not in seen:
                seen.add(name)
                mcp_servers.append({'name': name, 'config': cfg, 'source': 'settings.json'})

    # Priority 4: ~/.claude/plugins/*/settings.json
    plugins_dir = home / '.claude' / 'plugins'
    if plugins_dir.exists():
        for plugin_dir in sorted(plugins_dir.iterdir()):
            settings_file = plugin_dir / 'settings.json'
            if settings_file.exists():
                plugin_settings = load_json(settings_file)
                if plugin_settings and plugin_settings.get('mcpServers'):
                    for name, cfg in plugin_settings['mcpServers'].items():
                        if name not in seen:
                            seen.add(name)
                            src = f"plugins/{plugin_dir.name}/settings.json"
                            mcp_servers.append({'name': name, 'config': cfg, 'source': src})

    # Extract tools and capabilities
    mcp_tools = []
    capability_map = {}
    for entry in mcp_servers:
        cfg = entry.get('config', {})
        tools = cfg.get('tools', []) if isinstance(cfg, dict) else []
        if isinstance(tools, list):
            for tool in tools:
                tool_name = tool.get('name', '') if isinstance(tool, dict) else str(tool)
                if not tool_name:
                    continue
                capabilities = _extract_mcp_tool_capabilities(tool_name)
                tool_entry = {
                    'name': tool_name,
                    'server': entry['name'],
                    'source': entry['source'],
                    'capabilities': capabilities,
                }
                mcp_tools.append(tool_entry)
                # Build capability -> tool mapping
                for cap in capabilities:
                    capability_map.setdefault(cap, []).append(tool_name)

    return {
        'total_servers': len(mcp_servers),
        'servers': mcp_servers,
        'tools': mcp_tools,
        'capability_map': capability_map,
    }


def _extract_mcp_tool_capabilities(tool_name: str) -> list:
    """Extract capability keywords from an MCP tool name.

    Matches against _MCP_CAPABILITY_KEYWORDS patterns, returning the
    matching capability names (e.g. 'file', 'http').
    """
    name_lower = tool_name.lower()
    capabilities = []
    for cap, keywords in _MCP_CAPABILITY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            capabilities.append(cap)
    return capabilities if capabilities else ['unknown']


def scan_all() -> dict:
    """Scan both skills and MCP servers, return unified capability map."""
    skills_data = scan_skills()
    mcp_data = scan_mcp_servers()

    # Merge capability maps
    merged_map = dict(skills_data.get('capability_map', {}))
    for cap, handlers in mcp_data.get('capability_map', {}).items():
        for handler in handlers:
            key = f"{cap} (MCP)"
            merged_map.setdefault(key, []).append(handler)
    # MCP tools also added directly under their names
    for tool in mcp_data.get('tools', []):
        tool_name = tool['name']
        for cap in tool.get('capabilities', []):
            merged_map.setdefault(cap, []).append(tool_name)

    return {
        'skills': skills_data,
        'mcp': mcp_data,
        'capability_map': merged_map,
    }


def scan_skills(skills_dir: str = None) -> dict:
    """Scan skills directory and return capability map."""
    if skills_dir is None:
        skills_dir = Path.home() / '.claude' / 'skills'
    else:
        skills_dir = Path(skills_dir)

    if not skills_dir.exists():
        return {"error": f"Skills directory not found: {skills_dir}", "skills": []}

    skills = []
    capability_map = {}

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue

        skill_name = skill_path.name
        skill_md = skill_path / 'SKILL.md'

        if not skill_md.exists():
            # Try to find any .md file
            md_files = list(skill_path.glob('*.md'))
            if md_files:
                skill_md = md_files[0]
            else:
                continue

        try:
            content = skill_md.read_text(encoding='utf-8')
            fm = extract_frontmatter(content)

            name = fm.get('name', skill_name)
            description = fm.get('description', '')

            # Extract keywords for matching
            keywords = extract_keywords(content)

            # Extract version info
            version_info = extract_version(fm, skill_name)

            skill_entry = {
                "name": name,
                "directory": skill_name,
                "description": description[:200] if description else '',
                "keywords": keywords,
                "path": str(skill_path),
                "has_eval": (skill_path / 'evals').exists(),
                "version": version_info["version"],
                "version_source": version_info["source"],
                "semver": version_info["semver"],
            }

            skills.append(skill_entry)

            # Build keyword -> skill mapping
            for kw in keywords:
                capability_map.setdefault(kw, []).append(name)

            # Also map from description words
            desc_words = _RE_DESC_WORDS.findall(description.lower())
            for word in desc_words:
                if word not in _STOPWORDS and len(word) > 4:
                    capability_map.setdefault(word, []).append(name)

        except Exception as e:
            skills.append({
                "name": skill_name,
                "directory": skill_name,
                "error": str(e),
                "path": str(skill_path),
            })

    return {
        "skills_dir": str(skills_dir),
        "total": len(skills),
        "skills": skills,
        "capability_map": capability_map,
    }


def match_capability(capability: str, skills_data: dict) -> list:
    """Find skills matching a capability requirement."""
    capability_lower = capability.lower()
    matches = []
    partial = []

    for skill in skills_data.get('skills', []):
        if 'error' in skill:
            continue

        desc_lower = skill.get('description', '').lower()
        keywords = skill.get('keywords', [])

        # Direct match in description
        if capability_lower in desc_lower:
            matches.append((skill['name'], 'direct'))

        # Keyword match
        elif any(capability_lower in kw.lower() for kw in keywords):
            matches.append((skill['name'], 'keyword'))

        # Partial match (some overlap)
        elif any(word in desc_lower for word in capability_lower.split()):
            partial.append((skill['name'], 'partial'))

    return {"matches": matches, "partial": partial}


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Scan installed skills')
    parser.add_argument('--skills-dir', help='Path to skills directory')
    parser.add_argument('--capability', help='Match a specific capability')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--list', action='store_true', help='List all skills')
    parser.add_argument('--mcp', action='store_true', help='Scan MCP servers only')
    parser.add_argument('--all', action='store_true', help='Scan both skills and MCP servers')
    args = parser.parse_args()

    if args.mcp:
        data = scan_mcp_servers()
        print(f"Scanned {data['total_servers']} MCP servers, {len(data['tools'])} tools")
        for server in data['servers']:
            print(f"  * {server['name']} (from {server['source']})")
        if data['tools']:
            print(f"\n  Tools: {', '.join(t['name'] for t in data['tools'])}")
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.all:
        data = scan_all()
        s = data['skills']
        m = data['mcp']
        print(f"Skills: {s['total']} installed | MCP: {m['total_servers']} servers, {len(m['tools'])} tools")
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.capability:
        data = scan_skills(args.skills_dir)
        result = match_capability(args.capability, data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.list:
        data = scan_skills(args.skills_dir)
        for skill in data['skills']:
            if 'error' in skill:
                status = f"WARN: {skill.get('error', 'ok')}"
                print(f"[{status}] {skill['name']}")
            else:
                version = skill.get('version', 'unknown')
                has_eval = '*' if skill.get('has_eval') else ' '
                print(f"[*] {skill['name']:30s} v{version:15s} {skill.get('description', '')[:50]}")
        print(f"\nTotal: {data['total']} skills")
        print("Legend: [*] has eval  [ ] no eval")
    elif args.json:
        print(json.dumps(scan_skills(args.skills_dir), indent=2, ensure_ascii=False))
    else:
        data = scan_skills(args.skills_dir)
        print(f"Scanned {data['total']} skills from {data['skills_dir']}")
        for skill in data['skills']:
            if 'error' not in skill:
                print(f"  * {skill['name']}")

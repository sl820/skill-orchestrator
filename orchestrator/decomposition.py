"""
Task Decomposition Engine.
Breaks user requests into Goal/Inputs/Outputs/Capabilities.
"""

from __future__ import annotations
import re
from typing import Optional
from .models import Task, InputSpec, OutputSpec, Capability


# =============================================================================
# Action Words Patterns
# =============================================================================

ACTION_PATTERNS = [
    # Creation actions
    (r'\b(create|generate|make|build|produce)\b', 'generate'),
    # Analysis actions
    (r'\b(analyze|examine|review|assess|evaluate|calculate)\b', 'analyze'),
    # Extraction actions
    (r'\b(extract|parse|read|get|fetch|retrieve|scrape|crawl)\b', 'extract'),
    # Transformation actions
    (r'\b(transform|convert|process|format|translate)\b', 'transform'),
    # Visualization actions
    (r'\b(visualize|chart|plot|graph|render|display)\b', 'visualize'),
    # Presentation actions
    (r'\b(present|display|show|summarize|report)\b', 'present'),
    # Testing actions
    (r'\b(test|verify|check|validate|debug)\b', 'test'),
    # Design/Creation
    (r'\b(design|layout|style|theme|decorate)\b', 'design'),
    # Integration
    (r'\b(integrate|connect|link|combine|merge|unite)\b', 'integrate'),
    # Documentation
    (r'\b(write|document|draft|compose|author)\b', 'generate'),
]

# =============================================================================
# File Type Patterns
# =============================================================================

FILE_PATTERNS = [
    (r'\.pdf\b', 'pdf'),
    (r'\.docx?\b', 'word'),
    (r'\.xlsx?\b|\.csv\b|\bcsv\b|\.excel\b', 'spreadsheet'),
    (r'\.pptx?\b|\.powerpoint\b', 'presentation'),
    (r'\.html?\b|\.css\b|\.js\b', 'frontend'),
    (r'\.png\b|\.jpg\b|\.jpeg\b|\.gif\b|\.svg\b', 'visual-design'),
    (r'\.json\b|\.yaml\b|\.yml\b', 'data'),
    (r'\.md\b|\.markdown\b', 'documentation'),
    (r'\.py\b', 'code'),
    (r'\.sh\b', 'shell'),
]

# =============================================================================
# Output Format Patterns
# =============================================================================

OUTPUT_FORMAT_PATTERNS = [
    (r'\bpdf\b', 'pdf'),
    (r'\bword\b|\bdocx?\b', 'word'),
    (r'\bexcel\b|\bspreadsheet\b|\bxlsx?\b', 'spreadsheet'),
    (r'\bpptx?\b|\bpowerpoint\b|\bslides?\b|\bpresentation\b', 'presentation'),
    (r'\bwebsite\b|\bwebpage\b|\bhtml\b', 'frontend'),
    (r'\bimage\b|\bgraphic\b|\bposter\b|\bdesign\b', 'visual-design'),
    (r'\breport\b|\bsummary\b', 'documentation'),
    (r'\bchart\b|\bgraph\b|\bvisualization\b', 'visualize'),
]

# =============================================================================
# Capability Inference Patterns
# =============================================================================

CAPABILITY_PATTERNS = [
    # PDF
    (r'\bpdf\b|\bextract.*pdf\b|\bpdf.*text\b|\bmerge.*pdf\b|\bocr\b', 'pdf'),
    # Spreadsheet
    (r'\bspreadsheet\b|\bexcel\b|\bxlsx?\b|\bcsv\b|\bdata.*analysis\b|\banalyze.*data\b', 'spreadsheet'),
    # Presentation
    (r'\bpresentation\b|\bslides?\b|\bpptx?\b|\bpowerpoint\b|\bdeck\b', 'presentation'),
    # Word
    (r'\bword\b|\bdocx?\b|\breport\b|\bletter\b|\bdocument\b', 'word'),
    # Frontend
    (r'\bwebsite\b|\bwebpage\b|\bweb.*page\b|\bui\b|\bfrontend\b|\breact\b|\bhtml\b|\bcss\b', 'frontend'),
    # API
    (r'\bapi\b|\bsdk\b|\bllm\b|\bclaude.*integration\b', 'api'),
    # Documentation
    (r'\bdocumentation\b|\bproposal\b|\bspec\b|\btechnical.*writing\b', 'documentation'),
    # Internal comms
    (r'\binternal\b|\bannouncement\b|\bnewsletter\b|\bupdate\b', 'internal-comms'),
    # MCP
    (r'\bmcp\b|\bmodel.*context.*protocol\b', 'mcp'),
    # Art
    (r'\bgenerative.*art\b|\balgorithmic.*art\b|\bp5\.js\b|\bflow.*field\b', 'algorithmic-art'),
    # Visual design
    (r'\bposter\b|\bvisual.*art\b|\bflyer\b', 'visual-design'),
    # GIF
    (r'\bgif\b|\banimated.*gif\b', 'gif'),
    # Theme
    (r'\btheme\b|\bstyling\b', 'theme'),
    # Brand
    (r'\bbrand\b|\banthropic.*style\b', 'brand'),
    # React
    (r'\breact.*component\b|\bcomplex.*ui\b|\bshadcn\b', 'react-artifact'),
    # Testing
    (r'\btest\b|\bplaywright\b|\bscreenshot\b', 'testing'),
    # Web access
    (r'\bweb.*search\b|\bweb.*access\b|\bcrawl\b|\bscrape\b|\bbrowse\b', 'web-access'),
    # Skill
    (r'\bskill\b|\beval\b|\bbenchmark\b', 'skill-creation'),
]


# =============================================================================
# Preposition Patterns for Input/Output Detection
# =============================================================================

FROM_INPUT_PATTERNS = [
    r'\bfrom\b(.+?)(?:\band\b|\binto\b|\bto\b|\bfor\b|$)',
    r'\busing\b(.+?)(?:\band\b|\bto\b|\bfor\b|$)',
    r'\bbased on\b(.+?)(?:\band\b|\bto\b|\bfor\b|$)',
    r'\bwith\b(.+?)(?:\band\b|\bto\b|\bfor\b|$)',
]

TO_OUTPUT_PATTERNS = [
    r'\binto\b(.+?)(?:\band\b|\bfrom\b|\bfor\b|$)',
    r'\bto\b(.+?)(?:\band\b|\bfrom\b|\bfor\b|$)',
    r'\bas\b(.+?)(?:\band\b|\bfrom\b|\bfor\b|$)',
    r'\bgenerating\b(.+?)(?:\band\b|\bfrom\b|\bfor\b|$)',
]


def extract_action(text: str) -> str:
    """Extract the primary action verb from text."""
    text_lower = text.lower()
    for pattern, action in ACTION_PATTERNS:
        if re.search(pattern, text_lower):
            return action
    return 'generate'  # Default action


def extract_file_types(text: str) -> list[str]:
    """Extract file types mentioned in text."""
    found = []
    text_lower = text.lower()
    for pattern, ftype in FILE_PATTERNS:
        if re.search(pattern, text_lower):
            if ftype not in found:
                found.append(ftype)
    return found


def extract_output_formats(text: str) -> list[str]:
    """Extract output formats from text."""
    found = []
    text_lower = text.lower()
    for pattern, fmt in OUTPUT_FORMAT_PATTERNS:
        if re.search(pattern, text_lower):
            if fmt not in found:
                found.append(fmt)
    return found


def infer_capabilities(text: str) -> list[str]:
    """Infer capabilities needed from text."""
    found = []
    text_lower = text.lower()
    for pattern, cap in CAPABILITY_PATTERNS:
        if re.search(pattern, text_lower):
            if cap not in found:
                found.append(cap)
    return found


def extract_inputs_outputs(text: str) -> tuple[list[InputSpec], list[OutputSpec]]:
    """
    Extract input specifications and output specifications from text.

    Returns:
        Tuple of (inputs, outputs)
    """
    inputs = []
    outputs = []

    text_lower = text.lower()

    # Extract file inputs
    for pattern, ftype in FILE_PATTERNS:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            file_path = match.group(0)
            inp = InputSpec(
                type=ftype,
                path=file_path,
                description=f"Input file: {file_path}",
            )
            inputs.append(inp)

    # Extract URL inputs
    url_pattern = r'https?://[^\s]+'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        inp = InputSpec(
            type='url',
            path=url,
            description=f"URL input: {url}",
        )
        inputs.append(inp)

    # Extract output formats
    for fmt in extract_output_formats(text):
        out = OutputSpec(
            type=fmt,
            description=f"Output format: {fmt}",
        )
        outputs.append(out)

    return inputs, outputs


def decompose_task(user_request: str) -> Task:
    """
    Decompose a user request into Goal/Inputs/Outputs/Capabilities.

    Example:
        Input: "Create a presentation from sales.xlsx showing quarterly trends"
        Output: Task with:
            goal: "Create presentation from sales data"
            inputs: [InputSpec(type='spreadsheet', path='sales.xlsx')]
            outputs: [OutputSpec(type='presentation')]
            capabilities_needed: [Capability('spreadsheet', 'analyze'),
                                  Capability('presentation', 'generate')]
    """
    # Normalize whitespace
    normalized = ' '.join(user_request.split())

    # Extract components
    action = extract_action(normalized)
    file_types = extract_file_types(normalized)
    output_formats = extract_output_formats(normalized)
    inferred_caps = infer_capabilities(normalized)

    # Extract inputs and outputs
    inputs, outputs = extract_inputs_outputs(normalized)

    # Build capabilities
    capabilities = []
    for cap_name in inferred_caps:
        capability = Capability(
            name=cap_name,
            action=action,
        )
        capabilities.append(capability)

    # Build goal (clean version without file paths)
    goal = normalized

    task = Task(
        goal=goal,
        original_request=user_request,
        inputs=inputs,
        outputs=outputs,
        capabilities_needed=capabilities,
    )

    return task


def decompose_task_simple(request: str) -> dict:
    """
    Simple decomposition without full Task objects.
    Returns a dict for quick analysis.

    Example output:
    {
        "goal": "Analyze sales data and create presentation",
        "capabilities": [
            {"name": "spreadsheet", "action": "analyze"},
            {"name": "presentation", "action": "generate"},
        ],
        "inputs": [{"type": "file", "path": "sales.csv"}],
        "outputs": [{"type": "presentation"}],
    }
    """
    task = decompose_task(request)

    return {
        "goal": task.goal,
        "original": task.original_request,
        "capabilities": [
            {"name": c.name, "action": c.action}
            for c in task.capabilities_needed
        ],
        "inputs": [
            {"type": i.type, "path": i.path, "description": i.description}
            for i in task.inputs
        ],
        "outputs": [
            {"type": o.type, "description": o.description}
            for o in task.outputs
        ],
    }


def format_task_decomposition(task: Task) -> str:
    """Format a Task as a human-readable decomposition."""
    lines = []
    lines.append(f"Task: {task.goal}")
    lines.append("")

    if task.inputs:
        lines.append("Inputs:")
        for inp in task.inputs:
            lines.append(f"  - {inp.type}: {inp.description}")
        lines.append("")

    if task.outputs:
        lines.append("Outputs:")
        for out in task.outputs:
            lines.append(f"  - {out.type}: {out.description}")
        lines.append("")

    lines.append("Capabilities needed:")
    for i, cap in enumerate(task.capabilities_needed, 1):
        lines.append(f"  {i}. {cap.name} → {cap.action}")

    return "\n".join(lines)

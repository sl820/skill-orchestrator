# Skill Orchestrator

A production-grade meta-skill for Claude Code that sits between the user and all other skills, acting as an intelligent router and execution planner.

## Features

- **Task Decomposition**: Automatically breaks down user requests into executable steps
- **Skill Matching**: Matches user intent to the best available skill using keyword and semantic analysis
- **Risk Assessment**: Multi-dimensional risk scoring before execution
- **Gap Detection**: Identifies missing capabilities and offers installation suggestions
- **Execution Planning**: Builds dependency graphs for optimal parallel execution
- **Cost Estimation**: Token and time cost estimates before execution

## Installation

```bash
# Clone the repository
git clone https://github.com/sl820/skills-orchestrator.git
cd skills-orchestrator

# Or add as a submodule to your Claude skills directory
```

## Usage

### CLI

```bash
# Scan installed skills
python -m orchestrator.main

# Create execution plan
python -m orchestrator.main plan "analyze CSV and generate chart"

# Execute request
python -m orchestrator.main execute "create a presentation from sales.xlsx"
```

### Python API

```python
from orchestrator import invoke, create_orchestrator

# Auto-execution entry point
result = invoke("analyze CSV file and generate chart")
print(result["skills"])  # List of installed skills
print(result["plan"])    # Execution plan

# Create orchestrator manually
orchestrator = create_orchestrator()
plan = orchestrator.plan("your request here")
```

## Architecture

```
orchestrator/
├── __init__.py          # Auto-execution entry point
├── cli.py               # CLI interface
├── config.py            # Configuration constants
├── models.py            # Data models
├── decomposition.py     # Task decomposition engine
├── mapping.py           # Capability-to-skill mapping
├── scoring.py           # Confidence scoring
├── conflict.py          # Skill conflict resolution
├── risk.py              # Risk assessment
├── dependency_graph.py  # Execution dependency graph
├── executor.py          # Plan executor
├── retry.py             # Retry logic
├── failure.py           # Failure handling
├── control_flow.py      # Control flow syntax
├── progress.py           # Progress tracking
├── cost.py               # Cost estimation
├── versioning.py        # Version tracking
├── preferences.py        # User preference learning
├── integration.py       # Main orchestrator class
└── post_execution.py    # Post-execution review
```

## Execution Modes

| Mode | When to Use | Behavior |
|------|------------|----------|
| **AUTO** | Low risk, reversible | Execute immediately |
| **SUGGEST** | Moderate risk | Show plan, wait for confirmation |
| **PLAN** | High risk or gaps | Show detailed plan, wait for approval |
| **THINK** | User asks "how would you" | Show reasoning, don't execute |

## Configuration

Configuration is in `orchestrator/config.py`:

```python
CONFIDENCE_WEIGHTS = {
    "keyword": 0.25,
    "semantic": 0.25,
    "historical": 0.25,
    "coverage": 0.15,
    "recency": 0.10,
}

RISK_WEIGHTS = {
    "risk_level": 0.30,
    "reversibility": 0.20,
    "cross_system": 0.20,
    "skill_count": 0.15,
    "user_expertise": 0.15,
}
```

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License - see LICENSE file for details.

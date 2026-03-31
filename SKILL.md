---
name: skill-orchestrator
description: >
  Production-grade skill orchestration meta-skill. Use when: user describes any goal (vague or
  specific), task spans multiple domains or skills, user asks "what skills do I have" or
  "列出我安装的 skills", user wants to coordinate multiple skills, a capability gap is suspected,
  or executing any complex multi-step workflow. Proactively analyzes tasks, decomposes them into
  executable plans, matches against installed skills, detects missing capabilities and offers
  to install them. Skills: orchestration, task planning, skill routing, capability matching,
  multi-skill coordination, skill gap detection, execution planning.
metadata:
  version: "1.0.0"
---

# Skill Orchestrator

A production-grade meta-skill that sits between the user and all other skills, acting as an intelligent router and execution planner.

---

## WHEN THIS SKILL IS TRIGGERED — EXECUTE THIS WORKFLOW

**Do NOT just display this document. Actually run the steps below.**

### STEP 1: Scan Installed Skills

**RUN THIS COMMAND NOW:**
```bash
python3 ~/.claude/skills/skill-orchestrator/scripts/scan_skills.py --all
```

Present the results to the user:
- List all installed skills (name, version if known, brief description)
- List any MCP servers found (count and names)
- Note: Only `web-access` has a version (v2.4.1) — all others show "unknown" because they lack `metadata.version` in frontmatter

### STEP 2: Analyze the User's Request

Ask only if the request is vague. Break it into:
- **Goal**: What does the user want to accomplish?
- **Inputs**: What does the user already have?
- **Outputs**: What format should the result be?
- **Capabilities needed**: What must happen to get from input to output?

Produce a Task Decomposition like this:
```
Task: [one-line summary]
Capabilities needed:
1. [capability] → [specific action]
2. [capability] → [specific action]
...
```

### STEP 3: Match Capabilities to Skills

For each capability in the decomposition, use the **Capability-to-Skill Mapping table** (see below in Reference) to find the best matching skill(s). Flag each as:
- ✅ **AVAILABLE**: exact skill match exists
- ⚠️  **PARTIAL**: a skill exists but may have gaps
- ❌ **MISSING**: no skill for this capability

### STEP 4: If Gaps Exist — Offer to Install

For each MISSING capability, tell the user:
> "This task requires [capability] but no skill for it is installed. You can:
> [1] Install it now (takes ~2 min)
> [2] Use a workaround with existing skills
> [3] Skip this part
> [4] Cancel the task"

### STEP 5: Build the Execution Plan

Based on the execution mode:
- **AUTO** (low risk, reversible): Execute immediately after a one-line heads-up
- **SUGGEST** (moderate risk): Show the plan, wait for "好"/"是"/"执行"
- **PLAN** (high risk or gaps present): Show detailed plan with rationale, wait for explicit approval
- **THINK** (user asked "how would you" or uncertain): Show reasoning but don't execute until asked

Plan format:
```
## Execution Plan

Task: [summary]
Mode: [AUTO/SUGGEST/PLAN/THINK]
Skills used: [list]
Order: 1 → 2 → 3

Steps:
1. [Skill A] — [what it does]
   Input: [needed]
   Output: [produced]

2. [Skill B] — [what it does]
   Input: [step 1 output + user input]
   Output: [produced]
```

### STEP 6: Execute the Plan

- Follow the order in the plan
- For each step, invoke the appropriate skill
- Report progress: `[Step N/M] skill → status`
- If a skill fails: try its alternative, then stop and report the error
- Do NOT skip steps or change the plan without informing the user

### STEP 7: Post-Execution

- Summarize what was done and which skills were used
- If any PARTIAL matches were used, note what a better skill could do
- Ask: "Want to install any missing skills for better coverage next time?"

---

## Reference: Capability-to-Skill Mapping

Use this table to match user request capabilities to installed skills:

| Capability Keywords | Primary Skill | Alternative |
|-------------------|--------------|-------------|
| pdf, extract text, merge pdf, ocr, watermark | `pdf` | `docx` |
| spreadsheet, excel, data analysis, chart, csv | `xlsx` | `canvas-design` |
| presentation, slides, deck, powerpoint | `pptx` | `canvas-design` |
| word, docx, letter, report, formal document | `docx` | `doc-coauthoring` |
| website, web page, ui, react, html, css, dashboard | `frontend-design` | `web-artifacts-builder` |
| api, sdk, claude integration, llm app | `claude-api` | `mcp-builder` |
| documentation, proposal, spec, technical writing | `doc-coauthoring` | `docx` |
| internal comms, announcement, newsletter, update | `internal-comms` | `docx` |
| mcp server, model context protocol, tool integration | `mcp-builder` | — |
| generative art, algorithmic, p5.js, flow field | `algorithmic-art` | `canvas-design` |
| poster, visual art, flyer, png, pdf design | `canvas-design` | `pptx` |
| gif, slack animation | `slack-gif-creator` | `algorithmic-art` |
| theme, styling, consistent look | `theme-factory` | `brand-guidelines` |
| brand colors, anthropic style | `brand-guidelines` | `theme-factory` |
| react artifact, complex ui, shadcn | `web-artifacts-builder` | `frontend-design` |
| testing, playwright, screenshot, browser | `webapp-testing` | `web-access` |
| web search, scraping, browser, login-required | `web-access` | — |
| skill creation, eval, benchmark | `skill-creator` | — |

---

## Reference: MCP Discovery

Scan MCP servers from these locations (in priority order):

| Priority | Source | Path |
|----------|--------|------|
| 1 | Global MCP | `~/.claude/mcp.json` |
| 2 | Project MCP | `.claude/mcp.json` |
| 3 | Settings | `~/.claude/settings.json` (field: `mcpServers`) |
| 4 | Plugins | `~/.claude/plugins/*/settings.json` |

**Implementation:** `python3 ~/.claude/skills/skill-orchestrator/scripts/scan_skills.py --all`

## Reference: MCP Capability Keywords

Match MCP tool names to capability categories:

| Category | Tool Name Keywords |
|----------|-------------------|
| `file` | read, write, delete, copy, move, exists, stat, glob |
| `http` | fetch, request, get, post, put, delete, api |
| `database` | query, execute, select, insert, update, delete, db |
| `shell` | bash, shell, exec, command, run, script |
| `git` | commit, push, pull, branch, checkout, clone, git |
| `browser` | click, type, screenshot, navigate, evaluate, dom |
| `search` | search, find, query, grep, match |
| `memory` | remember, recall, store, get, search |

## Reference: Handler Ranking

When multiple handlers match a capability:

1. **Skills** with exact/primary match → confidence 0.85–0.95
2. **MCP Tools** with direct capability match → confidence 0.70–0.90
3. **Skills** with partial/inferred match → confidence 0.50–0.70

Present matches with source indicator: `(Skill)` or `(MCP Server)`

## Reference: Conflict Resolution

When two skills compete, score by 5 dimensions:

```
Score = Precision×0.30 + Coverage×0.25 + Performance×0.20
       + UserPreference×0.15 + Recency×0.10
```

| Score Gap | Resolution |
|-----------|------------|
| ≥ 0.30 | **AUTO** — select winner, inform user |
| 0.15–0.30 | **HYBRID** — recommend, ask confirm |
| < 0.15 | **MANUAL** — list options |

Conflict display format:
```
Skill Conflict:
  web-artifacts-builder: 0.88 ★ (Primary React)
  frontend-design:        0.75    (React OK)
  Resolution: HYBRID (gap: 0.13)
  [1] web-artifacts-builder (recommended)
  [2] frontend-design
  [3] Use both
```

User overrides: "总是用 X" (prefer), "不要用 X" (avoid)

## Reference: Confidence Scoring

```
Confidence = keywordScore×0.25 + semanticScore×0.25
           + historicalSuccess×0.25 + coverageScore×0.15
           + recencyBoost×0.10
```

Levels: EXCELLENT 90-100% | GOOD 70-89% | MODERATE 50-69% | WEAK 30-49% | POOR 0-29%

When confidence < 70%: suggest next-best fallback.
If no fallback ≥ 50%: flag as **GAP**, offer to install.

Gap severity: **BLOCKING** (cannot proceed) | **MAJOR** | **MINOR** | **ADVISORY**

Known incompatibilities:
- `canvas-design` + `pdf`: use `pdf` first to extract content, then `canvas-design`
- `frontend-design` + `web-artifacts-builder`: use isolated component trees

---

## Phase 4: Execution Planning

After matching and gap resolution, build an **Execution Plan**.

### Execution Modes

| Mode | When to Use | Behavior |
|------|------------|---------|
| **AUTO** | Risk score ≤ 0.25, low complexity | Execute immediately, inform user |
| **SUGGEST** | Risk score 0.26–0.50, moderate complexity | Show plan, execute after one-word confirmation ("好", "是", "执行") |
| **PLAN** | Risk score 0.51–0.75, high complexity or gaps | Show detailed plan with rationale, wait for explicit approval |
| **THINK** | User asks "how would you", "分析一下", or high uncertainty | Show reasoning and plan but don't execute until asked |
| **ADAPTIVE** | Mid-execution, a skill fails or new information emerges | Re-plan dynamically, inform user of change |

### Multi-Dimensional Risk Assessment

Mode selection is based on a **weighted risk score** across 5 dimensions:

#### Risk Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Risk Level** | 0.30 | Inherent risk of the task operations |
| **Reversibility** | 0.20 | How easily can changes be undone |
| **Cross-System** | 0.20 | Does task span multiple systems/domains |
| **Skill Count** | 0.15 | Number of skills involved |
| **User Expertise** | 0.15 | User's assumed experience level |

#### Risk Level Definitions

| Level | Score | Characteristics | Examples |
|-------|-------|-----------------|----------|
| **Low** | 0.2 | Read-only, no system modification, fully reversible | Reading files, API GET, data visualization |
| **Medium** | 0.5 | Minor side effects, semi-reversible | Creating files, API writes, config changes |
| **High** | 0.75 | Significant changes, difficult to reverse | File deletions, database writes, deployment |
| **Critical** | 1.0 | Irreversible, security-sensitive, production-impacting | `rm -rf`, production DB writes, security config |

#### Reversibility Assessment

| Level | Score | Description |
|-------|-------|-------------|
| **Easily Reversible** | 0.2 | Can undo in one step, no side effects |
| **Semi-Reversible** | 0.5 | Can revert with effort, some side effects |
| **Difficult** | 0.75 | Requires manual intervention to undo |
| **Irreversible** | 1.0 | Cannot undo, permanent changes |

#### Risk Score Calculation

```
Total Risk Score = (
  riskLevel × 0.30 +
  reversibility × 0.20 +
  crossSystem × 0.20 +
  skillCount × 0.15 +
  userExpertise × 0.15
)
```

#### Mode Selection Thresholds

| Risk Score | Mode | Confidence |
|------------|------|------------|
| ≤ 0.25 | **AUTO** | 85% |
| 0.26–0.50 | **SUGGEST** | 75% |
| 0.51–0.75 | **PLAN** | 80% |
| > 0.75 or Critical risk present | **THINK** | 90% |

#### Dynamic Mode Adjustment

During execution, if remaining risk drops significantly (e.g., < 50% of original), modes can be **de-escalated** (PLAN→SUGGEST). If complications arise, modes can be **escalated** (SUGGEST→PLAN).

**Mode selection rules** (apply in order):

1. If user explicitly says "直接做", "执行吧", "auto" → **AUTO**
2. If any step has Critical risk level → **THINK**
3. If user asks a how/would/analysis question → **THINK**
4. If any capability is flagged **MISSING** → **PLAN** (must resolve gaps first)
5. Calculate risk score and select mode by threshold
6. Default → **SUGGEST**

### Execution Plan Format

```
## 执行计划

**任务理解**: [1-2 sentence summary]

**Skill 清单**:
✅ [installed skill] - [reasoning]
⚠️  [partial match] - [with alternatives]
❌ [missing skill] - [offer to install]

**决策**:
- 执行模式: [MODE]
- 使用的 skills: [list]
- 顺序: [numbered list with dependency arrows]

**执行步骤**:
1. [Skill A] [auto/suggest]
   输入: [what it needs]
   输出: [what it produces]
   前置依赖: [none / step N output]

2. [Skill B] [auto/suggest]
   输入: [step 1 output + any user input]
   输出: [what it produces]
   前置依赖: [step 1]

[...]

**预计产出**: [final deliverable]
```

---

## Phase 5: Orchestrated Execution

### Execution Rules

1. **Inform before acting** — Even in AUTO mode, a brief "我用 x → y → z 的顺序执行" keeps the user oriented
2. **Respect the mode** — Don't skip confirmation steps in SUGGEST/PLAN modes
3. **Skill calling is sequential by default** — Output of step N is input to step N+1 unless explicitly parallel
4. **Parallel when safe** — Independent steps (e.g., fetching web data AND reading a local file) can run concurrently
5. **Monitor and report** — For PLAN/AUTO, report progress at each step completion

### Dependency Graph Builder

Build a **dependency graph** to determine parallel execution boundaries. This replaces the vague "independent steps" rule with explicit dependency types.

#### Dependency Types

| Type | Symbol | Description | Allows Parallel? |
|------|--------|-------------|-----------------|
| **DATA** | `A --data--> B` | A's output is B's input | No (must wait) |
| **CONTROL** | `A --ctrl--> B` | B waits for A to complete | No (must wait) |
| **RESOURCE** | `A ═════ B` | Both need same resource | Only if shared/locked |
| **CONDITIONAL** | `A --if--> B` | B runs only if A meets condition | Depends on condition |
| **OPTIONAL** | `A --?--> B` | B can run independently, uses A if available | Yes |

#### Parallel Group Computation

Use Kahn's algorithm (topological sort) to compute parallel execution groups:

```
┌─ STEP 1 ──────────────────────────────────────────────────────┐
│ ⚡ pdf:extract_tables  ✅ pending                               │
│   └─ Input: sales_report.pdf                                  │
└────────────────────────────────────────────────────────────────┘

┌─ PARALLEL [2 steps] ───────────────────────────────────────────┐
│ ⚡ xlsx:analyze_data    ⚡ canvas-design:create_chart          │
│   └─ from step 1 (data)  └─ from step 1 (data)               │
└────────────────────────────────────────────────────────────────┘

┌─ STEP 3 ──────────────────────────────────────────────────────┐
│ ⚡ pptx:generate_slides  ✅ pending                           │
│   └─ from step 2 (tables, charts)                             │
└────────────────────────────────────────────────────────────────┘
```

#### Dependency Graph Visualization

For PLAN mode, display the dependency graph:

```
Dependency Graph:
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Plan                              │
└─────────────────────────────────────────────────────────────────┘

Step 1: pdf:extract_tables
  └─ Output: { tables: 3, rowCount: 156 }
         │
         ├──data ──► Step 2a: xlsx:analyze_data
         │              └─ Output: { metrics: {...} }
         │
         └──data ──► Step 2b: canvas-design:create_chart
                        └─ Output: { chartImage: "..." }

Step 3: pptx:generate_slides
  └─ Input: { tables: step2a, chart: step2b }
       │
       📊 Critical Path: step1 → step2a → step3
       ⏱️  Estimated Duration: 45 seconds
       🔀 Parallel Groups: [step1] → [step2a, step2b] → [step3]
```

#### Deadlock Detection

Before execution, check for circular dependencies:
- Use DFS cycle detection on the dependency graph
- If cycle detected, flag the involved steps and suggest resolution
- Break the weakest dependency (typically RESOURCE with shared mode)

#### Error Recovery

When a skill fails during execution:
- Try alternative skill for same capability (if available)
- If no alternative, stop and inform user with specific error
- Don't silently skip failed steps

### Failure Handling Modes

Choose a failure handling strategy based on task risk:

| Mode | Behavior | When to Use |
|------|----------|-------------|
| **FAIL_FAST** | Stop on first failure, rollback changes | High-risk irreversible tasks |
| **FAIL_SOFT** | Try alternatives, skip if none available | Moderate risk, fallbacks exist |
| **CONTINUE** | Execute all steps, report at end | Low risk, partial results valuable |

### Control Flow Syntax

For complex tasks, express conditional execution:

```
IF <condition> THEN <step> ELSE <fallback>
RETRY <n> ON <condition>
SKIP-IF <condition> <step>
ROLLBACK-ON <condition>
```

**Condition Examples**:
- `step1.success` — step 1 succeeded
- `step1.rowCount > 0` — step 1 returned data
- `error.code == 'PARSE_ERROR'` — specific error occurred
- `attempt < 3` — retry counter condition

### Retry Policy

For recoverable errors, use exponential backoff:

```yaml
step:
  id: step1
  skill: pdf
  action: extract_tables
  retry_on:
    condition: "error.code == 'PARSE_ERROR' && attempt < 3"
    delay: 1000        # initial delay ms
    backoff: exponential
    max_delay: 10000   # max delay ms
```

### Failure Handling Display

During execution with failures:

```
Execution Status:
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: pdf:extract_tables                                     │
│ ├─ Attempt 1: PARSE_ERROR (recoverable)                       │
│ ├─ Attempt 2: Success ✅                                       │
│ └─ Output: { tables: 3, rows: 156 }                            │
│                                                                 │
│ Step 2: xlsx:analyze_data                                      │
│ ├─ ⚠️  No data rows found (step1.rowCount == 0)                 │
│ ├─ SKIP-IF triggered, using fallback                           │
│ └─ Fallback: canvas-design:create_chart ✅                       │
│                                                                 │
│ Step 3: pptx:generate_slides                                   │
│ ├─ Input: { tables: step1, chart: step2_fallback }             │
│ └─ Success ✅ (12 slides generated)                             │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐    │
│ │ Summary:                                                 │    │
│ │ ✅ Completed: 3/3                                        │    │
│ │ ⚠️  Fallbacks used: 1                                    │    │
│ │ 🔄 Retries: 1                                            │    │
│ │ ⏱️  Total Duration: 23s                                  │    │
│ └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Rollback Actions

For destructive operations, define rollback procedures:

```yaml
step:
  id: cleanup_old_files
  skill: filesystem
  action: delete
  targets: ["/tmp/cache/*"]
  rollback_on: "failed"  # If this fails, undo is not possible - warn user
  warning: "Irreversible operation - ensure targets are correct"
```

### Progress Reporting

During execution, use this format:

```
[Step 1/3] pdf → 读取文件... 完成 (提取了 3 个表格)
[Step 2/3] xlsx → 分析数据... 完成 (计算了利润率)
[Step 3/3] pptx → 生成幻灯片... 完成 (12 页)
✅ 全部完成
```

---

## Phase 6: Post-Execution Review

After completing a multi-skill task:

1. Summarize what was done and what skills were used
2. If a step had a suboptimal match (PARTIAL), suggest the ideal skill that could replace it
3. Ask if the user wants to install any missing skills for better future coverage
4. Note any patterns — if this type of request keeps coming up, suggest creating a dedicated skill

### User Preference Learning

Track user preferences to improve future skill selection. Preferences are stored in memory and applied during conflict resolution.

#### Preference Signal Types

| Signal Type | Source | Weight | Effect |
|------------|--------|--------|--------|
| **vote** | User explicitly chooses a skill | 1.0 | Strong positive |
| **selection** | User picks from offered options | 0.8 | Positive |
| **usage** | User completes task with skill | 0.5 | Positive |
| **skip** | User skips alternative | -0.3 | Negative |
| **completion** | Task completed successfully | 0.3 | Positive |

#### Preference Storage Format

```yaml
user_preferences:
  - skill: web-artifacts-builder
    capability: react_component
    preference: 0.6        # -1.0 to +1.0
    confidence: 0.72        # 0.0 to 1.0
    source: implicit        # explicit | implicit | combined
    evidence:
      - type: usage
        timestamp: "2026-03-28T10:00:00Z"
      - type: usage
        timestamp: "2026-03-30T14:30:00Z"
    created_at: "2026-03-28T10:00:00Z"
    updated_at: "2026-03-30T14:30:00Z"
```

#### Preference Application

During conflict resolution, preferences adjust skill scores:

```
Score adjustment = preference × confidence × 0.2

Example:
  web-artifacts-builder base score: 0.88
  User preference: +0.6, confidence: 0.72
  Adjustment: +0.6 × 0.72 × 0.2 = +0.086
  Final score: 0.966 → AUTO-select
```

#### Explicit Preference Commands

Users can directly express preferences:
- **"总是用 X"** → Set `always_prefer` for skill X
- **"不要用 X"** → Set `always_avoid` for skill X
- **"忘了 X 的偏好"** → Clear preference for skill X

#### Preference Decay

Preferences decay over time to remain relevant:
- **Half-life**: 30 days
- **Expiry**: Confidence drops below 0.1 → preference removed
- **Boost**: Recent usage (7 days) → +10 recency boost

#### Privacy Settings

- Implicit data (usage patterns) stored locally by default
- Explicit preferences are user-controlled
- Preferences are **project-local** by default (not shared across projects)

### Preference Learning Display

```
学习到的偏好:
┌─────────────────────────────────────────────────────────────────┐
│  Skill: web-artifacts-builder                                   │
│  Capability: react_component                                    │
│  Preference: +0.6 🟢 (user prefers)                            │
│  Confidence: 72%                                                 │
│  Evidence: 3 usages in last 30 days                             │
│  Source: implicit inference                                     │
│  Applied: Score boost +0.086 during conflict resolution        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dynamic Skill Installation

When a gap is detected, offer this workflow:

```
## ❌ Skill 缺失检测

任务 "[task]" 需要 [Missing Skill] 但未安装。

**当前可用**:
- [List of installed skills that could partially substitute]

**推荐安装**:
- [Missing Skill]: [one-line description from known repo]

操作选项:
  [1] 立即安装 [Missing Skill] 并继续执行
  [2] 使用现有技能继续（可能效果打折）
  [3] 先看下 [Missing Skill] 的详细介绍再决定
  [4] 取消这个任务

请选择 [1-4]:
```

### Installation Sources Priority

1. **Built-in skills** — Installed at `~/.claude/skills/`
2. **GitHub: anthropics/skills** — `https://github.com/anthropics/skills/tree/main/skills`
3. **GitHub: other repos** — User-specified or discovered
4. **Custom build** — Use `skill-creator` to build a tailored skill

---

## 能力关键词索引

关键词匹配参见上方的 **Reference: Capability-to-Skill Mapping** 表格，其中包含了所有技能与其对应的能力关键词完整列表。该表格在 Skill Matching & Gap Detection 阶段用于将用户请求映射到对应技能。

---

## Cost/Resource Estimation

Provide cost estimates before execution so users can make informed decisions.

### Cost Categories

| Category | Unit | Description |
|----------|------|-------------|
| **Token** | tokens | Claude API token consumption |
| **Time** | seconds | Estimated execution time |
| **External API** | calls | External API invocations |
| **Filesystem** | ops | File read/write/delete operations |

### Estimation Precision Levels

| Level | Confidence | Based On | Accuracy |
|-------|------------|----------|----------|
| **PRECISE** | 90%+ | Historical data + input size | ±10% |
| **FORECAST** | 70-89% | Skill metadata | ±30% |
| **ESTIMATE** | 50-69% | Average defaults | ±50% |

### Cost Calculation

Per-skill cost profiles track historical execution data:

```yaml
skill_cost_profile:
  skill: xlsx
  static_token_cost: 5000      # tokens per invocation (baseline)
  per_input_char_cost: 0.5     # tokens per input character
  per_output_char_cost: 1.2   # tokens per output character
  static_time_cost: 5          # seconds (baseline)
  history:
    - timestamp: "2026-03-30T10:00:00Z"
      input_tokens: 4500
      output_tokens: 8000
      duration_ms: 4500
      success: true
    - timestamp: "2026-03-29T15:30:00Z"
      input_tokens: 5200
      output_tokens: 9500
      duration_ms: 5200
      success: true
```

### Cost Limit Configuration

Configure warning and critical thresholds:

```yaml
cost_limits:
  token:
    warning: 50000
    critical: 100000
  time:
    warning: 300      # seconds
    critical: 600
  external_api:
    warning: 10
    critical: 50
```

### Cost Estimate Display

```
Cost Estimation:
┌─────────────────────────────────────────────────────────────────┐
│ Task: analyze CSV + generate presentation                     │
│ Input: 10MB CSV file                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ⚡ Token Estimate: ~45,000 tokens (Precision: FORECAST)         │
│    ├─ xlsx:analyze_data: 12,000 tokens                        │
│    └─ pptx:generate_slides: 33,000 tokens                      │
│                                                                 │
│ ⏱️  Time Estimate: ~35 seconds (Precision: MEDIUM)             │
│    ├─ xlsx:analyze_data: 8 seconds                             │
│    └─ pptx:generate_slides: 27 seconds                        │
│                                                                 │
│ 🔌 API Calls: 0                                                │
│ 📁 File Ops: 3 (read CSV, write PPTX, log)                   │
│                                                                 │
│ Precision: FORECAST (based on skill metadata)                  │
│ Confidence: 78%                                                 │
│                                                                 │
│ ⚠️  Warnings: None                                             │
│                                                                 │
│ ✅ Ready to proceed                                             │
└─────────────────────────────────────────────────────────────────┘
```

### When to Show Cost Estimates

- **PLAN mode**: Always show full cost breakdown
- **SUGGEST mode**: Show summary (total tokens + time)
- **AUTO mode**: Show brief estimate if > 30 seconds or > 10K tokens
- **User asked**: Show on explicit request ("要花多少"/"cost")

### Cost Warning Escalation

```
⚠️  COST WARNING
┌─────────────────────────────────────────────────────────────────┐
│ Token usage will reach 85,000 (exceeds warning threshold 50K)  │
│ Current task: Generate 50-page PPT + detailed analysis          │
│                                                                 │
│ [1] Continue execution                                          │
│ [2] Reduce scope                                               │
│ [3] Cancel task                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Skill Version / Compatibility Tracking

Track skill versions and detect compatibility issues before execution.

### 10.1 Version Metadata Extraction

During skill discovery, extract version information from frontmatter:

| Source | Path | Priority |
|--------|------|----------|
| `metadata.version` | SKILL.md frontmatter | 1 (highest) |
| `version` | SKILL.md frontmatter | 2 |
| Directory suffix | `skill-name/v1.2.3/` | 3 |
| Git tag | `.git/refs/tags/` | 4 |

**Version format**: Follows [Semantic Versioning](https://semver.org/):
```
MAJOR.MINOR.PATCH[-prerelease][+build]
Examples: "1.0.0", "2.1.3", "3.0.0-alpha", "1.2.0+20260330"
```

#### Version Extraction Display

```
Skill Version Info:
┌─────────────────────────────────────────────────────────────────┐
│ Skill: web-access                                               │
├─────────────────────────────────────────────────────────────────┤
│  Installed: v2.4.1 (2026-03-15)                               │
│  Latest:    v2.5.0 (2026-03-28)                   🟡 UPDATE     │
│  Channel:   stable                                            │
│                                                                 │
│  Changelog:                                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ v2.5.0 [2026-03-28]                                      │  │
│  │   ✨ Enhanced cookie handling for social media sites    │  │
│  │   🐛 Fixed screenshot timing issue on dynamic pages     │  │
│  │                                                             │  │
│  │ v2.4.0 [2026-03-10]                                      │  │
│  │   ⚡ Added concurrent request batching (up to 5x faster) │  │
│  │   🔧 Improved login flow detection                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [1] Update to v2.5.0                                          │
│  [2] Stay on v2.4.1                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Compatibility Matrix

Track which skill versions work together and with the Claude Code environment.

#### Compatibility Dimensions

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Claude Code** | Min/max Claude Code version | `>= 0.4.0, < 1.0.0` |
| **Node.js** | Required Node.js version | `>= 18.0.0` |
| **Platform** | OS compatibility | `win32`, `darwin`, `linux` |
| **Dependencies** | Required external packages | `playwright >= 1.40` |
| **Skill Combos** | Verified working with other skills | `frontend-design >= 1.5` |

#### Compatibility Storage Format

```yaml
skill_compatibility_registry:
  skill: web-access
  version: "2.4.1"
  compatibility:
    claude_code:
      min: "0.5.0"
      max: "1.0.0"
      recommended: "0.6.x"
    node_js:
      min: "18.0.0"
      recommended: "22.x"
    platform:
      - win32
      - darwin
      - linux
    dependencies:
      - name: playwright
        min_version: "1.40.0"
        required: true
      - name: ws
        min_version: "8.16.0"
        required: false
    verified_combinations:
      - skill: frontend-design
        min_version: "1.5.0"
        status: verified
        last_tested: "2026-03-25"
      - skill: pdf
        min_version: "1.2.0"
        status: verified
        last_tested: "2026-03-20"
      - skill: xlsx
        min_version: "1.1.0"
        status: partial
        notes: "Large file transfers may timeout"
```

#### Compatibility Check Display

```
Compatibility Check:
┌─────────────────────────────────────────────────────────────────┐
│ Task: "Generate report from Excel and create webpage"          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ⚡ xlsx@1.3.2  ✅ COMPATIBLE                                     │
│    ├─ Claude Code: 0.6.1 ✅                                    │
│    ├─ Node.js: 22.12.0 ✅                                      │
│    ├─ Platform: win32 ✅                                       │
│    └─ Dependencies: playwright 1.45 ✅                         │
│                                                                 │
│ ⚡ frontend-design@1.8.0  ✅ COMPATIBLE                         │
│    ├─ Claude Code: 0.6.1 ✅                                    │
│    ├─ Node.js: 22.12.0 ✅                                      │
│    ├─ Platform: win32 ✅                                       │
│    └─ Dependencies: react 18.x ✅                              │
│                                                                 │
│ ⚡ web-access@2.4.1  ⚠️  PARTIAL                                │
│    ├─ Claude Code: 0.6.1 ✅                                    │
│    ├─ Node.js: 22.12.0 ✅                                      │
│    ├─ Platform: win32 ✅                                       │
│    └─ Dependencies: playwright 1.45 ✅                         │
│         ⚠️  playwright version mismatch (needs 1.50+)         │
│             Workaround: Use fallback playwright-chromium         │
│                                                                 │
│ ✅ Overall: Task can proceed (2/3 fully compatible)            │
└─────────────────────────────────────────────────────────────────┘
```

### 10.3 Breaking Change Impact Analysis

When upgrading or planning skill usage, analyze what might break.

#### Breaking Change Severity

| Severity | Icon | Impact | Requires |
|----------|------|--------|----------|
| **CRITICAL** | 🔴 | Complete failure, data loss risk | Explicit user approval |
| **MAJOR** | 🟠 | Significant feature loss, workflow broken | Confirmation |
| **MINOR** | 🟡 | Minor features degraded, workarounds exist | Inform user |
| **ADVISORY** | 🔵 | No functional impact, cosmetic/performance | Log only |

#### Breaking Change Detection

Detect breaking changes by analyzing version diffs:

```
Breaking Change Analysis: web-access v2.4.1 → v2.5.0
┌─────────────────────────────────────────────────────────────────┐
│ 🔴 CRITICAL: Login flow behavior changed                       │
│    Previous: Auto-detect login prompts, pause for 30s          │
│    New:       Immediate timeout after 10s                     │
│    Impact:    All login-required workflows affected            │
│    Mitigation: Update skill invocation to set extended_timeout │
│                                                                 │
│ 🟠 MAJOR: Response header format changed                       │
│    Previous: headers returned as dict                          │
│    New:       headers returned as list of tuples               │
│    Impact:    Any skill parsing headers directly breaks       │
│    Affected:  skill-orchestrator internal processing          │
│                                                                 │
│ 🟡 MINOR: Default user agent string updated                    │
│    Impact:    Some sites may detect differently                │
│    Workaround: Explicitly set user_agent in call              │
│                                                                 │
│ 🔵 ADVISORY: Internal API refactored                           │
│    No external impact                                          │
└─────────────────────────────────────────────────────────────────┘
```

#### Impact Scope Analysis

```
Impact Scope: Upgrading frontend-design 1.8.0 → 2.0.0
┌─────────────────────────────────────────────────────────────────┐
│  Skills affected by this upgrade:                               │
│                                                                 │
│  🟠 MAJOR impact on:                                            │
│     - skill-orchestrator (uses frontend-design extensively)    │
│     → All 6 orchestration workflows may need adjustment        │
│                                                                 │
│  🟡 MINOR impact on:                                            │
│     - pptx (shares HTML rendering utilities)                   │
│     → Minor rendering adjustments may be needed                 │
│                                                                 │
│  ✅ No impact on:                                               │
│     - pdf, xlsx, docx, canvas-design                           │
│                                                                 │
│  ⚠️  Recommendation: Test skill-orchestrator after upgrade     │
│                                                                 │
│  Estimated test time: ~10 minutes                              │
└─────────────────────────────────────────────────────────────────┘
```

### 10.4 Version Health Dashboard

```
Skill Health:
┌─────────────────────────────────────────────────────────────────┐
│  Skill               │ Installed │ Latest  │ Status            │
│──────────────────────│──────────-│─────────│───────────────────│
│  web-access          │ v2.4.1    │ v2.5.0  │ 🟡 Update needed  │
│  frontend-design     │ v1.8.0    │ v2.0.0  │ 🔴 Major update   │
│  skill-creator       │ v1.2.3    │ v1.2.3  │ 🟢 Up to date     │
│  canvas-design       │ v2.1.0    │ v2.1.0  │ 🟢 Up to date     │
│  pdf                 │ v1.3.1    │ v1.4.0  │ 🟡 Update needed  │
├──────────────────────┴───────────┴─────────┴───────────────────┤
│  ⚠️  2 updates available, 1 major (may require testing)        │
│  ✅ Run "skill-orchestrator --check-updates" for details        │
└─────────────────────────────────────────────────────────────────┘
```

### 10.5 Version Tracking in Execution Planning

During Phase 4 (Execution Planning), version information feeds into risk and compatibility assessments:

```
Enhanced Execution Plan with Version Tracking:
┌─────────────────────────────────────────────────────────────────┐
│  Task: "Create data dashboard from Excel"                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Skill selection with version awareness:                        │
│                                                                 │
│  ⚡ xlsx@1.3.2                                                  │
│     Confidence: 95% (GOOD 🟢🟢)                                  │
│     Version OK, no known issues                                │
│                                                                 │
│  ⚡ frontend-design@1.8.0 ⚠️                                     │
│     Confidence: 82% (GOOD 🟢🟢)                                  │
│     ⚠️  Newer version 2.0.0 available with breaking changes   │
│     Recommendation: Complete current task, then review upgrade  │
│                                                                 │
│  🔗 Verified combination: xlsx@1.3 + frontend-design@1.8     │
│     Tested: 2026-03-25, Status: stable                         │
│                                                                 │
│  Execution mode: SUGGEST (minor version advisory flagged)      │
└─────────────────────────────────────────────────────────────────┘
```

### 10.6 Version Update Workflow

When a version issue is detected:

```
## 🔔 Skill Version Update Recommendation

`frontend-design` has an important update available:

**Current**: v1.8.0 (2026-02-15)
**Latest**: v2.0.0 (2026-03-28)
**Type**: MAJOR (contains breaking changes)

⚠️  Breaking Changes:
- Component API signature changed (break: component props restructure)
- Theme config format updated (config migration required)

**Suggested Actions**:
  [1] Update now (recommended) — I will help migrate the config
  [2] Update later — continue using v1.8.0
  [3] View detailed changelog
  [4] Only patch version (v1.8.0 → v1.8.1, safe update)

Please select [1-4]:
```

### 10.7 Scan-Skills Version Extension

`scan_skills.py` implements version extraction with this signature:

```python
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
        match = _RE_VERSION_DIR.search(skill_name)  # pre-compiled regex
        if match:
            version = match.group(1)
            source = 'directory.name'

    return {
        "version": version or "unknown",
        "source": source or 'none',
        "semver": _parse_semver(version) if version else None,
    }
```

返回结构说明：
- `version`: 字符串版本号（如 `"2.4.1"`），未找到时为 `"unknown"`
- `source`: 来源标识（`metadata.version` | `frontmatter.version` | `directory.name` | `none`）
- `semver`: 解析后的结构（`{major, minor, patch, prerelease, build}`），解析失败时为 `None`

metadata:
  version: "1.0.0"

---

## Important Principles

- **Never assume you know all installed skills** — scan `~/.claude/skills/` at the start of every task
- **Never execute without informing** — even AUTO mode gets a one-line heads-up
- **Never skip gap detection** — missing skills are an opportunity, not an obstacle
- **Prefer composition over single-skill forcing** — if a task needs 3 skills, use 3 skills
- **THINK mode is underrated** — when uncertain, show your reasoning first
- **Error recovery is planning** — when something fails, the replan IS the response

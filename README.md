# Skill Orchestrator

A production-grade meta-skill for Claude Code — the **intelligent router** between you and all other skills.

## What Does It Do?

When you ask Claude to do something complex (like "analyze this CSV and make a chart"), Skill Orchestrator:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SKILL ORCHESTRATOR                              │
│                                                                         │
│  You: "analyze sales.csv and create a presentation"                      │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────┴──────────────────────────┐             │
│  │            1. TASK DECOMPOSITION                      │             │
│  │  Breaks down: "analyze CSV" + "create presentation"   │             │
│  └──────────────────────────┬──────────────────────────┘             │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────┴──────────────────────────┐             │
│  │            2. CAPABILITY MATCHING                      │             │
│  │  Maps to: spreadsheet (analyze) + pptx (present)      │             │
│  │  Confidence: 85% + 82%                              │             │
│  └──────────────────────────┬──────────────────────────┘             │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────┴──────────────────────────┐             │
│  │            3. RISK ASSESSMENT                        │             │
│  │  Score: 0.35 (MEDIUM) → SUGGEST mode              │             │
│  │  Reversibility: SEMI_REVERSIBLE                     │             │
│  └──────────────────────────┬──────────────────────────┘             │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────┴──────────────────────────┐             │
│  │            4. EXECUTION PLAN                          │             │
│  │                                                          │             │
│  │    Step 1: spreadsheet → analyze CSV                   │             │
│  │    Step 2: pptx → generate slides                     │             │
│  │    Parallel: No (Step 2 depends on Step 1)            │             │
│  └──────────────────────────────────────────────────────┘             │
│                              │                                         │
│                              ▼                                         │
│                        [Confirm? Y/N]                                 │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────┴──────────────────────────┐             │
│  │            5. EXECUTE & TRACK                       │             │
│  │  Progress: ████████████░░ 80%                       │             │
│  └──────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Example

**Your Request:**
```
"分析季度销售数据并生成PPT汇报"
```

**Orchestrator Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXECUTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task: 分析季度销售数据并生成PPT汇报
Mode: SUGGEST (risk: 0.38)
Skills: spreadsheet, pptx

Steps:
  1. [spreadsheet] 分析CSV数据
     Input: sales_q4.csv
     Output: 分析结果 (利润率、同比增长)

  2. [pptx] 生成演示文稿
     Input: 步骤1的分析结果
     Output: 季度汇报.pptx

Gap: None ✅

Cost: ~2,500 tokens | ~15秒

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Confirm? (好/是/执行)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Features

| Feature | Description |
|---------|-------------|
| **Task Decomposition** | 分解用户请求为"目标→输入→输出→能力"结构 |
| **Capability Matching** | 5因子置信度评分，精确匹配意图与技能 |
| **Risk Assessment** | 5维度风险评估（操作风险、可逆性、跨系统、技能数、用户经验） |
| **Gap Detection** | 缺失能力检测 + 安装建议 |
| **Dependency Graph** | 自动构建并行执行计划 |
| **Cost Estimation** | Token消耗与执行时间预估 |

## Execution Modes

```
                    ┌──────────────────┐
                    │   USER REQUEST    │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │ "how would you?"            │ Yes → THINK
              │ "分析一下..."                 │         (show plan only)
              └──────────────┬──────────────┘
                             │ No
              ┌──────────────┼──────────────┐
              │ Risk Score              │
              └──────────────┬──────────────┘
                    ┌────────┼────────┐
                    │0.0     │0.5     │1.0
                    │        │        │
              ┌─────┴─┐ ┌───┴──┐ ┌──┴────┐
              │  AUTO │ │SUGGEST│ │ PLAN  │
              │(≤0.25)│ │(0.26~)│ │(0.51~)│
              └───────┘ └──────┘ └───────┘
                    │        │        │
                    │   "好" │   "执行" │
                    │   "是" │   "确认" │
                    └────────┴────────┘
```

## Installation

```bash
# 方式1: 直接复制到 Claude skills 目录
cp -r skill-orchestrator ~/.claude/skills/

# 方式2: 从 GitHub 克隆
git clone https://github.com/sl820/skill-orchestrator.git
mv skill-orchestrator ~/.claude/skills/
```

## Usage

### CLI
```bash
# 扫描已安装的 skills
python -m orchestrator.main

# 创建执行计划
python -m orchestrator.main plan "analyze CSV and generate chart"

# 执行请求
python -m orchestrator.main execute "create presentation from sales.xlsx"
```

### Python API
```python
from orchestrator import invoke, create_orchestrator

# 自动执行入口
result = invoke("analyze CSV file and generate chart")
print(f"Skills: {len(result['skills'])}")
print(f"Plan: {result['plan']}")

# 手动创建 orchestrator
orchestrator = create_orchestrator()
plan = orchestrator.plan("your request here")
```

## Architecture

```
orchestrator/
├── __init__.py          # 自动化执行入口 (invoke, main)
├── cli.py               # 命令行接口
├── models.py            # 数据模型 (Task, ExecutionPlan, SkillMatch...)
├── decomposition.py      # 任务分解引擎
├── mapping.py           # 能力→技能 映射表
├── scoring.py           # 5因子置信度评分
├── conflict.py          # 技能冲突解决
├── risk.py              # 风险评估
├── dependency_graph.py  # Kahn算法拓扑排序
├── executor.py          # 计划执行引擎
├── retry.py             # 指数退避重试
├── failure.py           # 失败处理与回滚
├── control_flow.py      # IF/RETRY/SKIP 控制流
├── progress.py           # 执行进度跟踪
├── cost.py              # 成本估算
├── versioning.py        # 技能版本追踪
├── preferences.py        # 用户偏好学习
├── integration.py       # SkillOrchestrator 主类
└── post_execution.py    # 执行后回顾
```

## Capability Map

| 你的需求 | 匹配技能 | 置信度 |
|---------|---------|--------|
| 分析CSV/Excel数据 | `xlsx` | 90% |
| 创建PPT演示文稿 | `pptx` | 88% |
| 读写PDF文件 | `pdf` | 92% |
| 创建Word文档 | `docx` | 85% |
| 抓取网页内容 | `web-access` | 87% |
| 测试网页应用 | `webapp-testing` | 84% |
| 创建算法艺术 | `algorithmic-art` | 86% |
| ... | ... | ... |

## Risk Scoring Formula

```
Risk Score = risk_level × 0.30
           + reversibility × 0.20
           + cross_system × 0.20
           + skill_count × 0.15
           + user_expertise × 0.15
```

| 维度 | 权重 | 说明 |
|-----|-----|-----|
| risk_level | 0.30 | 操作本身的风险性 |
| reversibility | 0.20 | 操作是否可逆 |
| cross_system | 0.20 | 是否涉及多系统 |
| skill_count | 0.15 | 涉及技能数量 |
| user_expertise | 0.15 | 用户专业程度 |

## Contributing

Issues and PRs welcome!

## License

MIT License

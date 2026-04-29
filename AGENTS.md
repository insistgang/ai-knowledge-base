# AGENTS.md - AI 知识库助手项目规范

## 项目概述

本项目是个人 AI 技术知识库助手。系统从 GitHub Trending、Hacker News、arXiv、RSS 等信息源采集 AI/LLM/Agent 相关动态，经过 AI 分析、去重、评分和整理后，保存为结构化 JSON 知识条目，并为后续 Telegram、飞书或日报分发提供稳定数据源。

## 技术栈

- 语言: Python 3.12
- AI 编排: OpenCode 或 Codex + 国产大模型/兼容 OpenAI API 的模型
- 工作流: LangGraph
- 数据格式: JSON、Markdown、YAML
- 测试: pytest
- 版本控制: Git

## 编码规范

- Python 代码遵循 PEP 8。
- 变量和函数使用 `snake_case`，类名使用 `PascalCase`。
- 业务函数必须有 Google 风格 docstring。
- 应用代码禁止裸 `print()`，使用 `logging`；一次性调试脚本可在入口函数中少量输出。
- 禁止 `import *`。
- 文件编码统一 UTF-8。
- 采集、分析、整理逻辑要可测试，避免把外部 API 调用和核心转换逻辑混在一起。

## 项目结构

```text
ai-knowledge-base/
├── AGENTS.md
├── README.md
├── .env.example
├── .opencode/
│   ├── agents/
│   └── skills/
├── knowledge/
│   ├── raw/
│   └── articles/
├── pipeline/
├── workflows/
├── specs/
└── tests/
```

## 目录职责

- `.opencode/agents/`: Agent 角色定义文件。
- `.opencode/skills/`: 可复用 Skill 能力包。
- `knowledge/raw/`: 原始采集数据，保留来源字段和采集时间。
- `knowledge/articles/`: 清洗后的知识条目，每条一个 JSON 文件。
- `pipeline/`: 模型客户端、采集、分析、整理、成本统计等流水线代码。
- `workflows/`: LangGraph 状态定义和工作流图。
- `specs/`: 项目愿景、需求规格、设计决策和验收记录。
- `tests/`: 单元测试、评估测试和安全回归测试。

## 知识条目格式

每条知识以 JSON 文件存储在 `knowledge/articles/` 目录下。

```json
{
  "id": "github-20260429-001",
  "title": "Example AI Agent Project",
  "source": "github-trending",
  "source_url": "https://github.com/example/project",
  "collected_at": "2026-04-29T12:00:00Z",
  "summary": "一句话中文摘要，不超过 100 字。",
  "analysis": {
    "tech_highlights": ["multi-agent", "workflow"],
    "relevance_score": 8,
    "reason": "与 AI Agent 工程化实践直接相关。"
  },
  "tags": ["agent", "workflow", "open-source"],
  "audience": ["developer", "researcher"],
  "status": "draft"
}
```

必填字段: `id`, `title`, `source`, `source_url`, `collected_at`, `summary`, `tags`, `status`。

`status` 可选值: `draft`, `reviewed`, `published`, `archived`。

## Agent 角色概览

| 角色 | 文件 | 职责 |
| --- | --- | --- |
| 采集 Agent | `.opencode/agents/collector.md` | 从外部源采集候选技术动态，保留 URL、标题、来源、时间等原始信息。 |
| 分析 Agent | `.opencode/agents/analyzer.md` | 分析技术价值、适用人群、亮点和风险，输出结构化分析字段。 |
| 整理 Agent | `.opencode/agents/organizer.md` | 去重、格式化、补全标签、归档到 `knowledge/articles/`。 |

## 质量标准

- 知识条目必须可追溯到真实 `source_url`。
- 摘要必须是中文，且保留关键英文技术术语。
- `relevance_score` 范围为 1-10。
- 任何 AI 生成内容都要区分事实、推断和建议。
- 测试通过后再提交，关键流程要留下可复现命令。

## 红线

- 不编造不存在的项目、论文、数据源、评测结果或 URL。
- 不在日志、提交记录、测试样例中暴露 API Key、Token、Cookie 或私密配置。
- 不执行破坏性命令，例如 `rm -rf`、`git reset --hard`，除非用户明确要求。
- 不把 `.env`、缓存、临时输出、大模型响应全文直接提交到 Git。
- 不绕过规格文档直接扩展大功能；新增核心能力前先补 `specs/`。

## 常用命令

```bash
python3 --version
git status --short
python3 -m pytest
```


# AI 技术知识库项目总结

> 更新时间：2026-08-30
> 统计口径：当前本地工作区；知识数据最新日期为 2026-08-30。

## 1. 项目定位

本项目是一个面向 AI、LLM、Agent 和机器学习技术动态的个人知识库系统。系统以 GitHub 项目为当前主要信息源，通过模型分析、LangGraph 工作流审核、结构化存储、质量门禁、MCP 查询和 Dashboard 展示，形成可追溯的技术知识资产。

核心流程如下：

```text
GitHub 采集
  → LLM 分析与评分
  → Reviewer 审核
  → Reviser 修订
  → Organizer 标准化
  → Supervisor 规则检查
  → JSON 归档 / MCP 查询 / Dashboard 展示
```

## 2. 当前数据概况

| 指标 | 当前值 | 说明 |
|---|---:|---|
| 历史文章 JSON | 625 | 全部保留，作为采集审计记录 |
| canonical 有效知识 | 129 | 同一规范化来源 URL 仅展示最新记录 |
| 默认隐藏的历史重复 | 496 | 不删除，只在查询与展示层折叠 |
| 唯一文章 ID | 625 | 当前没有跨文件重复 ID |
| 重复来源 URL 组 | 29 | 属于早期重复采集形成的历史数据 |
| 原始采集文件 | 125 | 位于 `knowledge/raw/` |
| 成本指标文件 | 122 | 位于 `knowledge/metrics/` |
| 无效 JSON | 0 | 625 个文章文件均通过解析与完整性检查 |

当前 canonical 视图具有以下特征：

- 数据源全部为 `github-trending`。
- 129 条有效知识当前全部为 `draft`。
- 相关度评分范围为 5–10，平均约 7.6。
- 高频主题包括 `deep-learning`、`llm`、`agent`、`multi-agent`、`computer-use`、`machine-learning` 和 `open-source`。
- 本地最新条目来自 2026-08-30，包括 Stable Baselines3、Logseq、Awesome AI for Security 和 Foundation Models Framework Lab 等项目。

## 3. 已实现的核心能力

### 3.1 数据采集与分析

- GitHub 项目采集与已有来源去重。
- DeepSeek、Qwen、OpenAI 兼容模型统一客户端。
- 普通分析与深度分析模型路由。
- API 异常或预算耗尽时使用启发式分析降级。
- Token、调用次数和预估费用记录。

### 3.2 LangGraph 工作流

生产工作流由 9 个节点组成：

```text
plan → collect → analyze → review
                           ├─ pass → organize → supervise → save
                           ├─ fail → revise → review
                           └─ 超限 → human_flag → END
```

其中：

- Planner 控制采集策略和数量。
- Reviewer 从摘要质量、技术深度、相关性、原创性和格式五个维度评分。
- Reviser 根据审核反馈修订分析结果并重新进入审核。
- Supervisor 执行确定性的字段与规则检查。
- 只有真实完成并通过 LLM 审核的新文章才会标记为 `reviewed`；降级放行仍保持 `draft`。
- `dry-run` 模式不会写入文章、成本指标或人工审核文件。

### 3.3 查询与展示

- MCP JSON-RPC 服务提供：
  - `search_articles`
  - `get_article`
  - `knowledge_stats`
- Dashboard 展示文章、评分、标签、来源、状态和成本统计。
- MCP 与 Dashboard 都使用 canonical 视图，默认隐藏历史重复记录。
- GitHub Pages 可用于发布静态 Dashboard。

### 3.4 质量与工程保障

- JSON Schema/字段校验。
- 跨文件 ID 与来源 URL 审计。
- A/B/C 内容质量评分。
- 本地测试默认隔离可能产生模型费用的慢速测试。
- GitHub Actions 包含测试、LangGraph 采集、Schema 校验、语料审计、质量检查和 Dashboard 生成步骤。

## 4. Agent 与 Skill 资产

项目包含 5 个 Agent 角色：

| Agent | 主要职责 |
|---|---|
| Router | 判断任务类型并选择执行角色 |
| Collector | 采集候选项目与原始信息 |
| Analyzer | 提取摘要、技术亮点、评分和受众 |
| Organizer | 整理字段、标签和存储格式 |
| Supervisor | 执行最终质量检查与放行判断 |

当前 `.opencode/skills/` 中还包含：

- GitHub Trending 采集 Skill。
- 技术摘要 Skill。
- Darwin Skill。
- 女娲 Skill。

其中 Darwin Skill 和女娲 Skill 属于额外引入的独立能力包，不是生产采集流水线的必需组件。

## 5. 其他配套内容

### 5.1 教程与项目文档

`content/wechat/yanlu-liangang/` 包含 10 篇课程文章和 41 张配图，主题覆盖：

1. 环境配置
2. Memory 工程
3. Sub-Agent
4. Skill
5. Hook
6. Pipeline 与 MCP
7. CI/CD 与 Dashboard
8. 成本控制
9. Multi-Agent
10. LangGraph

`specs/` 保存项目愿景以及 V2–V6 的成本控制、多 Agent、LangGraph、采集质量和生产完整性验收规格。

### 5.2 V4 产品原型

`v4-production/` 是一份产品化实验快照，包含：

- 知识库聊天 Bot。
- `/search`、`/today`、`/top`、`/subscribe` 等意图处理。
- Markdown/Telegram 日报格式化。
- Telegram Publisher 与 Console dry-run。
- OpenClaw 工作区与 Skill 示例。
- 独立的流水线、测试、规格和知识样本镜像。

这些能力目前属于原型或镜像，尚未全部并入主生产入口。

### 5.3 软件著作权材料

`output/` 保存了多套软件说明书、源代码文档和审核报告，覆盖：

- 多源信息采集与智能分析系统。
- 基于 LangGraph 的工作流编排系统。
- 知识库查询与管理系统。
- 技术情报自动化推送系统。
- AI 知识库质量评估与 CostGuard 系统。

## 6. 当前能力边界

| 能力 | 状态 |
|---|---|
| GitHub 自动采集 | 已实现 |
| LLM 分析与成本统计 | 已实现 |
| LangGraph 审核闭环 | 已实现 |
| MCP 查询 | 已实现 |
| canonical 去重展示 | 已实现 |
| Dashboard 与 CI/CD | 已实现 |
| Telegram 推送 | 原型 |
| OpenClaw 集成 | 原型 |
| RSS 采集 | 仅有占位配置 |
| Hacker News 采集 | 规划中 |
| arXiv 采集 | 规划中 |
| 飞书推送 | 规划中 |

## 7. 当前需要关注的问题

1. 知识数据已持续更新到 2026-08-30；本次工作流切换推送后，需要观察首次定时任务能否按 LangGraph 新入口稳定运行。
2. canonical 记录目前全部为 `draft`，尚未形成稳定的人工确认或发布机制。
3. 历史重复来源较多，虽然查询层已经折叠，但仍应保留审计监控，防止重新出现重复采集。
4. 标签存在大小写不统一，例如 `llm` 与 `LLM`，后续可增加标签规范化。
5. V4 Bot 及 Telegram/OpenClaw 原型与主流水线仍是两套路径，继续扩展前应先决定是否正式合并。
6. 部分学习路线文档仍保留旧进度描述，需要与当前 V6 实现状态同步。
7. 当前工作区仍有未提交修改；发布到远端前需要统一检查、提交并推送。

## 8. 建议的后续优先级

1. 审核并提交当前生产完整性修复，使远端 CI/CD 正式采用 LangGraph 入口。
2. 观察推送后的首次 GitHub Actions 运行，确认测试、LangGraph、审计和 Dashboard 全链路通过。
3. 建立 `draft → reviewed → published` 的人工审核与发布流程。
4. 统一标签大小写、别名和主题分类体系。
5. 从 RSS 或 arXiv 中选择一个作为第二数据源，验证多源采集能力。
6. 决定是否把 Telegram 日报作为正式输出渠道并接入主工作流。
7. 更新课程路线图、README 和项目简历中的版本状态。

## 9. 主要入口

| 用途 | 文件 |
|---|---|
| 生产工作流 | `pipeline/workflow_runner.py` |
| 流水线基础能力 | `pipeline/pipeline.py` |
| canonical 数据视图 | `pipeline/article_store.py` |
| LangGraph 图定义 | `pipeline/workflow_graph.py` |
| Reviewer/Reviser | `workflows/` |
| MCP 查询服务 | `mcp_knowledge_server.py` |
| Dashboard 生成 | `reports/generate_dashboard.py` |
| 语料完整性审计 | `hooks/audit_corpus.py` |
| 测试套件 | `tests/` |
| 项目规范 | `AGENTS.md` |

## 10. 常用验证命令

```bash
# 本地测试
python -m pytest

# 无写入演练
python -m pipeline.workflow_runner --sources github --limit 3 --dry-run

# Schema 校验
python hooks/validate_json.py knowledge/articles/*.json

# 全库身份与来源审计
python hooks/audit_corpus.py knowledge/articles/*.json --fail-on-duplicate-id

# 内容质量评分
python hooks/check_quality.py knowledge/articles/*.json

# 生成 Dashboard
python reports/generate_dashboard.py
```

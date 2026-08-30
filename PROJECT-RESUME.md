# AI 知识库系统 — 项目简历

## 📌 项目名称

**基于多 Agent 协作的 AI 技术知识库系统**

## 📋 项目简介

设计并实现了一个 AI 技术知识库系统，采用多 Agent 协作架构，实现从 GitHub 数据采集、智能分析、质量审核到结构化入库的自动化闭环。系统基于 LangGraph 状态机编排，支持 MCP 协议查询、可视化 Dashboard 和 Telegram Bot 原型交互。

## 🎯 核心职责

- 设计并实现 9 节点 LangGraph 工作流，包含条件路由和审核循环
- 开发 5 个 Agent 角色（Router/Collector/Analyzer/Organizer/Supervisor），实现任务分发和质量控制
- 构建 CostTracker 成本控制系统，实现调用追踪、预算预警和超限降级
- 编写安全防护原型与回归检查，覆盖输入清洗、PII 过滤、速率限制和审计日志
- 实现 Telegram Bot 原型，支持知识查询和 Skill 路由
- 开发 MCP Server，提供 JSON-RPC 2.0 接口供外部系统查询

## 🏗️ 技术架构

```
┌───────────────────────────────────────────────────────────────┐
│                      CLI  /  MCP  /  Dashboard                │
└───────────────────────────┬───────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                    LangGraph 工作流 (9 节点)                    │
│                                                               │
│   plan ─► collect ─► analyze ─► review ─► organize           │
│                         ▲          │                          │
│                         │    ┌─────┼─────┐                    │
│                         │    │     │     │                    │
│                         │  pass revise human_flag             │
│                         │          │     │                    │
│                         └──────────┘     ▼                    │
│                                        END                   │
│              organize ─► supervise ─► save ─► END            │
└───────────────────────────────────────────────────────────────┘
│
┌───────────────────────────▼───────────────────────────────────┐
│                    Agent Team (5 角色)                         │
│   Router → Collector / Analyzer / Organizer / Supervisor      │
└───────────────────────────────────────────────────────────────┘
│
┌───────────────────────────▼───────────────────────────────────┐
│                        存储层                                  │
│   knowledge/raw/  →  knowledge/articles/  →  MCP Server       │
└───────────────────────────────────────────────────────────────┘
```

## 💻 技术栈

| 类别 | 技术 |
|------|------|
| 编程语言 | Python 3.12 |
| AI 框架 | LangGraph + LangChain |
| 大模型 | DeepSeek / Qwen / OpenAI |
| 交互原型 | Telegram Bot API |
| 数据格式 | JSON / Markdown / YAML |
| 协议 | MCP (JSON-RPC 2.0) / HTTP |
| 部署 | GitHub Actions + GitHub Pages |
| 测试 | pytest + unittest |

## 🔧 核心模块

### 1. LangGraph 工作流引擎

```python
# 9 节点状态机
plan → collect → analyze → review → revise → organize → supervise → save → human_flag

# 3 路条件路由
if review_passed:
    return "organize"       # 通过 → 整理入库
elif iteration < max_iter:
    return "revise"         # 未通过 → 定向修改
else:
    return "human_flag"     # 超限 → 人工介入
```

### 2. Agent 角色定义

| Agent | 职责 |
|-------|------|
| Router | 任务分发，根据意图路由到对应 Agent |
| Collector | 从 GitHub Search API 采集近期活跃项目，过滤历史重复 URL |
| Analyzer | 智能分析，LLM 提取技术亮点和评分 |
| Organizer | 整理入库，去重、格式化、归档 |
| Supervisor | 质量审核，5 维加权评分（≥7.0 通过） |

### 3. 成本控制系统

```python
class CostTracker:
    """跨节点追踪模型调用，并提供预算状态与日报指标。"""

    def add_call(self, source, item_name, model, usage):
        # 记录每次 LLM 调用的 token 用量

    def is_budget_exceeded(self):
        # 判断预算是否耗尽，触发后续节点降级

    def to_daily_payload(self, date_str, generated_at):
        # 生成按来源和模型分组的成本日报
```

### 4. 安全防护原型

```python
# 四层防护
1. sanitize_input(text)     # 输入清洗（防 Prompt 注入）
2. filter_output(text)      # 输出过滤（PII 检测与掩码）
3. RateLimiter.check()      # 速率限制（滑动窗口）
4. AuditLogger.log()        # 审计日志（可追溯）
```

### 5. MCP Server

```python
# JSON-RPC 2.0 接口
{
    "method": "tools/call",
    "params": {
        "name": "search_articles",
        "arguments": {"keyword": "agent"}
    }
}

# 3 个工具
- search_articles  # 搜索知识库
- get_article      # 获取单篇文章
- knowledge_stats  # 获取 canonical/原始数量、评分和标签统计
```

### 6. Telegram Bot

```python
# 意图识别 + 指令系统
/search <query>   # 搜索知识库
/today             # 今日最新动态
/top               # 高分推荐文章
/subscribe         # 订阅每日日报
/help              # 显示帮助

# Skill 路由
- daily-digest     # 每日简报
- top-rated        # 高分推荐
```

## 📊 项目数据

| 指标 | 数值 |
|------|------|
| 版本化文件 | 1000+ |
| 本地测试 | 123 个（全部通过，2 个付费评估默认隔离） |
| 自动化 | GitHub Actions 每日采集与 GitHub Pages 发布 |
| Agent 角色 | 5 个 |
| 工作流节点 | 9 个 |
| MCP 工具 | 3 个 |
| 知识条目 | 625 条历史记录 / 129 条 canonical 知识 |
| 数据完整性 | 625/625 ID 唯一，历史重复 URL 非破坏性折叠 |

## 🎯 项目亮点

1. **架构设计精妙**：9 节点 LangGraph 状态机 + 5 Agent 协作，实现完整的质量闭环
2. **质量保障体系**：Reviewer 5 维评分 → Reviser 定向修改 → 循环审核 → HumanFlag 人工兜底
3. **成本控制与降级**：CostTracker 跨节点追踪 + 预算状态 + 超限降级
4. **数据完整性治理**：历史 URL 去重 + canonical 查询视图 + 全库 ID 审计
5. **多入口访问**：Telegram Bot 原型 + Skill 路由 + MCP Server + Dashboard
6. **工程规范完善**：SDD 规格 + 123 个本地测试 + CI/CD 自动化

## 📈 版本演进

| 版本 | 阶段 | 核心能力 |
|------|------|----------|
| V1 | 手动版 | Agent + Skill + 手动三步走 |
| V2 | 自动版 | Pipeline + Hooks + CI/CD |
| V3 | 工程增强 | Multi-Agent + CostTracker + 安全回归原型 |
| V4 | 产品原型 | Telegram Bot + MCP + Dashboard |
| V5 | 采集质量 | 历史 URL 去重 + 均衡查询 + 活跃度过滤 |
| V6 | 生产完整性 | LangGraph 定时链路 + canonical 视图 + 语料审计 |

## 🔗 项目链接

- **GitHub 仓库**: https://github.com/insistgang/ai-knowledge-base
- **可视化知识库**: https://insistgang.top/ai-knowledge-base/

## 📝 简历项目描述（可直接复制）

### 版本 1（详细版）

**基于多 Agent 协作的 AI 技术知识库系统**

- 设计并实现 9 节点 LangGraph 工作流，包含条件路由和审核循环，实现从数据采集到查询展示的全流程闭环
- 开发 5 个 Agent 角色（Router/Collector/Analyzer/Organizer/Supervisor），实现任务分发和质量控制
- 构建 CostTracker 成本控制系统，实现调用追踪、预算预警和超限降级
- 实现历史 URL 去重、canonical 查询视图和全库 ID 审计，保留原始记录的同时减少查询噪声
- 实现 Telegram Bot 交互原型和 Skill 路由
- 开发 MCP Server，提供 JSON-RPC 2.0 接口供外部系统查询
- 编写 123 个本地测试，覆盖单元测试、工作流集成、数据完整性和评估测试，全部通过
- 使用 GitHub Actions 实现每日 LangGraph 自动采集和 GitHub Pages 发布

**技术栈**：Python 3.12 / LangGraph / DeepSeek / Telegram Bot API / MCP / GitHub Actions

### 版本 2（精简版）

**基于多 Agent 协作的 AI 技术知识库系统**

- 采用 LangGraph 状态机编排 9 个工作流节点，实现多 Agent 协作和质量闭环
- 设计 5 个 Agent 角色（Router/Collector/Analyzer/Organizer/Supervisor），实现任务分发和质量控制
- 实现成本控制、历史去重和 canonical 查询视图，保障系统稳定运行
- 集成 Telegram Bot 原型、MCP 查询和可视化 Dashboard
- 编写 123 个本地测试，全部通过，使用 GitHub Actions 实现 CI/CD

**技术栈**：Python / LangGraph / DeepSeek / Telegram Bot API / MCP / GitHub Actions

### 版本 3（一句话版）

**AI 知识库系统**：基于 LangGraph 的多 Agent 协作架构，实现自动采集、智能分析、审核修订、成本控制和去重检索，集成 Telegram Bot 原型与 MCP Server，123 个本地测试全部通过。

---

## 🎓 面试话术

### 项目介绍（1分钟）

> 我做了一个基于多 Agent 协作的 AI 技术知识库系统。简单来说，就是用 LangGraph 搭建了一个 9 节点工作流，包含 5 个 Agent 角色，实现从 GitHub 自动采集 AI 项目、用 LLM 分析评分、审核修订到结构化入库和 MCP 查询的完整流程。
>
> 核心亮点有三个：第一是质量闭环，Reviewer 5 维评分不通过会自动打回修改，最多循环 3 次；第二是成本控制，CostTracker 贯穿分析、审核和修订节点，预算耗尽后自动降级；第三是数据完整性，在保留全部历史记录的同时，通过 canonical 视图隐藏重复内容，并用全库审计保证 ID 唯一。
>
> 目前系统保留了 625 条可追溯采集记录，经 canonical 去重后提供 129 条有效知识，123 个本地测试全部通过，并持续记录每次模型调用成本。

### 技术难点（被问到时）

> 最难的是 LangGraph 的条件路由设计。比如 review 节点，要根据评分决定是通过、打回修改还是人工介入，这三条路径的状态管理很复杂。我用 TypedDict 定义 KBState，每个节点只修改自己负责的字段，避免状态混乱。
>
> 另一个难点是成本控制。多 Agent 系统一次工作流会在分析、审核和修订节点多次调用 LLM。我让共享 CostTracker 贯穿所有节点，统一记录 token 和估算成本，达到预算后让后续审核节点安全降级，并把指标写入每日成本报告。

### 项目收获

> 这个项目让我理解了 AI Agent 的工程化实践。以前觉得 Agent 就是调 API，做完这个项目才知道，生产级的 Agent 需要考虑质量控制、成本控制、安全防护、可观测性等等。特别是 SDD（Spec-Driven Development）的思想，先写规格再写代码，测试就是和 AI 之间的合同。

---

**生成时间**：2026-05-07
**项目作者**：刘钢 (Francis)

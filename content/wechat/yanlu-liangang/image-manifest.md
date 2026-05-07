# 研路炼钢公众号配图命名清单

> 公众号名称：研路炼钢  
> 系列名称：从 0 到 1 搭建 AI 知识库  
> 用途：确保 10 篇公众号文章中的配图文件名、文章编号和主题一一匹配。

## 封面图命名

| 文章编号 | 文章文件 | 公众号文章标题 | 封面图文件名 |
| --- | --- | --- | --- |
| 01 | `01-environment.md` | 我为什么先把环境搭好：研究生做 AI 工程，第一步不是写代码 | `images/01-environment-cover.png` |
| 02 | `02-memory.md` | 给 AI 知识库加记忆：我不想再让信息只在当天有用 | `images/02-memory-cover.png` |
| 03 | `03-subagents.md` | 我为什么拆 Sub-agents：一个 AI 不该同时负责所有事 | `images/03-subagents-cover.png` |
| 04 | `04-skills.md` | 把经验沉淀成 Skills：别让每次协作都从零解释 | `images/04-skills-cover.png` |
| 05 | `05-hooks.md` | 给流程加 Hooks：把“记得检查”变成系统自动做 | `images/05-hooks-cover.png` |
| 06 | `06-pipeline-mcp.md` | 把 AI 工作流接成一条线：从脚本到 MCP Pipeline | `images/06-pipeline-mcp-cover.png` |
| 07 | `07-cicd-dashboard.md` | 给自己的项目装一块仪表盘：CI/CD 与 Dashboard 复盘 | `images/07-cicd-dashboard-cover.png` |
| 08 | `08-cost-control.md` | AI 工具越用越贵之后，我开始认真做成本控制 | `images/08-cost-control-cover.png` |
| 09 | `09-multi-agent.md` | 多智能体不是开很多窗口，而是重新分配责任 | `images/09-multi-agent-cover.png` |
| 10 | `10-langgraph.md` | 用 LangGraph 理解工作流：让 AI 从对话走向状态机 | `images/10-langgraph-cover.png` |

## 正文配图（已生成）

| 文章编号 | 配图文件 | 用途 | 状态 |
| --- | --- | --- | --- |
| 01 | `images/01-environment-overview.png` | 项目总览：数据采集到 Dashboard 全局视图 | ✅ 已有 |
| 02 | `images/02-memory-evolution.png` | 项目演进：Pipeline 到多智能体 LangGraph | ✅ 已有 |
| 03 | `images/03-subagents-concept-map.png` | 第 8-10 节知识全景概念图 | ✅ 已有 |
| 04 | `images/04-skills-file-mapping.png` | 项目文件与工程概念对应关系图 | ✅ 已有 |
| 05 | — | hooks 检查链路图 | ❌ 缺失 |
| 06 | — | pipeline 编排与 MCP 查询服务边界图 | ❌ 缺失 |
| 07 | — | Dashboard 指标与轻量 CI/CD 流程图 | ❌ 缺失 |
| 08 | `images/08-cost-control-section.png` | 成本控制策略图 | ✅ 已有 |
| 09 | `images/09-multi-agent-section.png` | 多智能体协作架构图 | ✅ 已有 |
| 10 | `images/10-langgraph-concept.png` | LangGraph 概念：状态 + 节点 + 边 | ✅ 已有 |
| 10 | `images/10-langgraph-comparison.png` | 线性 Pipeline vs LangGraph 对比 | ✅ 已有 |
| 10 | `images/10-langgraph-kbstate.png` | KBState 核心状态对象 | ✅ 已有 |
| 10 | `images/10-langgraph-five-nodes.png` | 五个节点函数职责详解 | ✅ 已有 |
| 10 | `images/10-langgraph-file-order.png` | 五个核心文件阅读顺序 | ✅ 已有 |
| 10 | `images/10-langgraph-recap.png` | 第 10 节学习成果复盘 | ✅ 已有 |

## 10 LangGraph 补充配图（17 张，可选使用）

| 配图文件 | 内容 |
|----------|------|
| `10-langgraph-stateflow.png` | 状态流与节点职责 |
| `10-langgraph-kbstate-detail.png` | KBState 共享数据对象详解 |
| `10-langgraph-state-machine.png` | 状态机图 |
| `10-langgraph-kbstate-v2.png` | KBState 数据对象图解（版本2） |
| `10-langgraph-node-responsibility.png` | 节点职责详解图 |
| `10-langgraph-conditional-edges.png` | 条件边路由图解 |
| `10-langgraph-execution-paths.png` | 三种执行路径 |
| `10-langgraph-file-mapping.png` | 概念到项目文件映射 |
| `10-langgraph-build-graph.png` | build_workflow_graph 函数连线图 |
| `10-langgraph-routing-functions.png` | 条件路由函数图解 |
| `10-langgraph-workflow-flowchart.png` | workflow_graph.py 流程图 |
| `10-langgraph-execution-trace.png` | run_workflow() 执行追踪图 |
| `10-langgraph-file-test-mapping.png` | 文件与测试映射图 |
| `10-langgraph-mental-model.png` | 工作流心智模型 |
| `10-langgraph-kbstate-dataflow.png` | KBState 执行中数据变化 |
| `10-langgraph-supervise-gate.png` | supervise 质量门路径图 |
| `10-langgraph-factory-analogy.png` | 工厂流水线类比图 |

## 命名规则

1. 封面图统一使用：`images/{文章编号}-{英文主题}-cover.png`。
2. 内文图统一使用：`images/{文章编号}-{英文主题}-{图用途}.png`。
3. 文章正文的 `配图文件名` 字段必须与本清单中的封面图文件名一致。
4. 如果后续生成实际图片，优先保存到 `content/wechat/yanlu-liangang/images/`。
5. 不覆盖已有图片；需要重做时使用 `-v2.png` 后缀。

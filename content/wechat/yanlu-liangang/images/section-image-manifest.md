# 研路炼钢公众号正文配图清单

> 来源：`.codex/generated_images/` 中通过 imagegen 技能生成的教学信息图
> 整理日期：2026-05-06
> 总计：29 张（已全部复制到本目录）

## 文章配图分布

### 01 环境搭建
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `01-environment-cover.png` | 封面图 | ✅ 已有 |
| `01-environment-overview.png` | 正文配图 | 项目总览：从数据采集到 Dashboard 发布的全局视图 |

### 02 Memory 工程
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `02-memory-cover.png` | 封面图 | ✅ 已有 |
| `02-memory-evolution.png` | 正文配图 | 项目演进：从自动化 Pipeline 到多智能体 LangGraph 工作流 |

### 03 Sub-agents
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `03-subagents-cover.png` | 封面图 | ✅ 已有 |
| `03-subagents-concept-map.png` | 正文配图 | 概念图：第 8-10 节学到的知识全景 |

### 04 Skills
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `04-skills-cover.png` | 封面图 | ✅ 已有 |
| `04-skills-file-mapping.png` | 正文配图 | 项目文件与工程概念的对应关系图 |

### 05 Hooks
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `05-hooks-cover.png` | 封面图 | ✅ 已有 |
| — | 正文配图 | ❌ 缺失 |

### 06 Pipeline / MCP
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `06-pipeline-mcp-cover.png` | 封面图 | ✅ 已有 |
| — | 正文配图 | ❌ 缺失 |

### 07 CI/CD Dashboard
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `07-cicd-dashboard-cover.png` | 封面图 | ✅ 已有 |
| — | 正文配图 | ❌ 缺失 |

### 08 成本控制
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `08-cost-control-cover.png` | 封面图 | ✅ 已有 |
| `08-cost-control-section.png` | 正文配图 | AI 知识库项目中的成本控制策略图 |

### 09 多智能体
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `09-multi-agent-cover.png` | 封面图 | ✅ 已有 |
| `09-multi-agent-section.png` | 正文配图 | 多智能体协作架构图 |

### 10 LangGraph
| 配图文件 | 用途 | 说明 |
|----------|------|------|
| `10-langgraph-cover.png` | 封面图 | ✅ 已有 |
| `10-langgraph-concept.png` | 开头场景 | LangGraph 概念：状态 + 节点 + 边 |
| `10-langgraph-comparison.png` | 这节做了什么 | 对比：线性 Pipeline vs LangGraph 工作流 |
| `10-langgraph-kbstate.png` | 关键产物 | KBState：贯穿工作流的核心状态对象 |
| `10-langgraph-five-nodes.png` | 我真正学到的 | 五个节点函数的职责详解 |
| `10-langgraph-file-order.png` | 行动清单 | 五个核心文件的阅读顺序指南 |
| `10-langgraph-recap.png` | 结尾金句 | 第 10 节学习成果与工程思维复盘 |

### 10 LangGraph 补充配图（可选内文图）
| 配图文件 | 内容说明 |
|----------|----------|
| `10-langgraph-stateflow.png` | 状态流与节点职责 |
| `10-langgraph-kbstate-detail.png` | KBState 共享数据对象详解 |
| `10-langgraph-state-machine.png` | 状态机图 |
| `10-langgraph-kbstate-v2.png` | KBState 数据对象图解（版本2） |
| `10-langgraph-node-responsibility.png` | 节点职责详解图 |
| `10-langgraph-conditional-edges.png` | 条件边路由图解 |
| `10-langgraph-execution-paths.png` | 三种执行路径：成功/无数据/审核失败 |
| `10-langgraph-file-mapping.png` | 概念到项目文件的映射 |
| `10-langgraph-build-graph.png` | build_workflow_graph 函数连线图 |
| `10-langgraph-routing-functions.png` | 条件路由函数图解 |
| `10-langgraph-workflow-flowchart.png` | workflow_graph.py 流程图 |
| `10-langgraph-execution-trace.png` | run_workflow() 执行追踪图 |
| `10-langgraph-file-test-mapping.png` | 文件与测试映射图 |
| `10-langgraph-mental-model.png` | LangGraph 工作流心智模型 |
| `10-langgraph-kbstate-dataflow.png` | KBState 执行中的数据变化 |
| `10-langgraph-supervise-gate.png` | 工作流路径与 supervise 质量门 |
| `10-langgraph-factory-analogy.png` | 工厂流水线类比图 |

## 缺配图的文章

| 文章 | 状态 | 说明 |
|------|------|------|
| 05 Hooks | ❌ 缺正文图 | 需要生成：hooks 检查链路图、脚本→GitHub Actions 流程图 |
| 06 Pipeline/MCP | ❌ 缺正文图 | 需要生成：pipeline 编排流程图、MCP 查询服务边界图 |
| 07 CI/CD Dashboard | ❌ 缺正文图 | 需要生成：Dashboard 指标图、轻量 CI/CD 流程图 |

## 命名规则

- 封面图：`{编号}-{主题}-cover.png`
- 正文配图：`{编号}-{主题}-{用途}.png`
- 补充配图：`{编号}-{主题}-{具体内容}.png`

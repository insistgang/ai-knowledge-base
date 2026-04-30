# 多 Agent 路由规则

## 第 9 节目标

将知识库流水线从单 Agent 手动执行升级为 **Router + Supervisor** 管理的多 Agent 协作模式：Router 在入口处识别任务类型并分发到正确的 Agent，Supervisor 在关键节点审核质量并决定放行、打回或阻断。这一架构实现关注点分离，让每个 Agent 职责单一、可独立测试，同时由 Supervisor 统一把关。

## Agent 职责表

| Agent | 职责 | 写文件 | 访问网页 | 执行命令 |
|-------|------|:---:|:---:|:---:|
| `router` | 识别任务类型，选择目标 Agent | 否 | 否 | 否 |
| `collector` | 采集外部信息源原始数据，不落盘 | 否 | 是 | 否 |
| `analyzer` | 分析已有数据，评分、亮点、标签 | 否 | 是 | 否 |
| `organizer` | 整理为标准 JSON 条目并写入 `knowledge/articles/` | 是 | 否 | 否 |
| `supervisor` | 审核各阶段产出，输出质量报告 | 否 | 否 | 否 |

## 任务路由表

| 用户意图 | task_type | target_agent | 说明 |
|----------|-----------|-------------|------|
| 采集信息、抓取数据 | `collect` | `collector` | 从 GitHub/HN/arXiv/RSS 提取原始候选条目 |
| 分析、评估、打分 | `analyze` | `analyzer` | 读取 raw 数据，生成技术分析 |
| 整理、保存、归档 | `organize` | `organizer` | 去重、格式化为标准条目并落盘 |
| 审核、校验、检查质量 | `review` | `supervisor` | 审查产出是否符合规范标准 |
| 完整流水线执行 | `pipeline` | `collector` | 第一步采集，后续由主流程串联 |
| 无法匹配以上场景 | `unknown` | `ask_human` | 暂停并请求用户澄清意图 |

### 路由优先级

1. 用户明确提到「采集」「抓取」「获取数据」→ `collect`
2. 用户明确提到「分析」「打分」「评估」→ `analyze`
3. 用户明确提到「整理」「保存」「归档」「生成条目」→ `organize`
4. 用户明确提到「审核」「校验」「检查质量」→ `review`
5. 涉及多个步骤的完整流程 → 按第一步路由（通常为 `collect`）
6. 均不匹配 → `unknown`

## Supervisor 触发条件

Supervisor 在以下任一条件满足时被激活：

| 触发条件 | 说明 |
|----------|------|
| 批量处理 ≥10 条 | 大规模操作需质量把关 |
| 写入或覆盖 `knowledge/articles/` | 入库操作必须有审核 |
| `relevance_score` 为 9-10 | 顶级评分需二次确认 |
| 成本、dashboard、metrics 对外展示 | 对外数据必须可信 |
| 字段缺失、格式错误、来源不明 | 存在质量风险 |
| 安全红线触碰预警 | 敏感操作需人工确认 |

## 标准路由输出

Router Agent 的输出格式（来自 `router.md`）：

```json
{
  "task_type": "collect",
  "target_agent": "collector",
  "reason": "用户要求采集本周 GitHub Trending AI 项目 Top 5。",
  "needs_supervisor": false
}
```

```json
{
  "task_type": "review",
  "target_agent": "supervisor",
  "reason": "用户要求审核 knowledge/articles/ 下 15 条目的质量。",
  "needs_supervisor": true
}
```

## 标准审核输出

Supervisor Agent 的输出格式（来自 `supervisor.md`）：

```json
{
  "status": "needs_revision",
  "score": 0.84,
  "findings": [
    {
      "severity": "medium",
      "field": "tags",
      "issue": "标签 'open-source' 过于宽泛，无法体现项目具体特征",
      "suggestion": "替换为更精细的标签，如 'agent-framework' 或 'llm-tool'"
    },
    {
      "severity": "medium",
      "field": "summary",
      "issue": "摘要含空洞词 '强大'，缺乏具体技术描述",
      "suggestion": "重新表述为包含具体技术能力的摘要"
    },
    {
      "severity": "low",
      "field": "summary",
      "issue": "摘要长度 112 字，略超建议的 100 字上限",
      "suggestion": "精简至 100 字以内"
    }
  ],
  "next_action": "revise"
}
```

```json
{
  "status": "blocked",
  "score": 0.40,
  "findings": [
    {
      "severity": "high",
      "field": "source_url",
      "issue": "source_url 不可访问，返回 404，来源真实性存疑",
      "suggestion": "更换为可验证的真实 URL 或标记为待确认并移除此条目"
    },
    {
      "severity": "high",
      "field": "id",
      "issue": "缺少必填字段 id",
      "suggestion": "补全 id 字段，格式为 {source}-{date}-{seq}"
    },
    {
      "severity": "high",
      "field": "relevance_score",
      "issue": "relevance_score 为 15，超出 1-10 有效范围",
      "suggestion": "修正评分至 1-10 范围内"
    }
  ],
  "next_action": "ask_human"
}
```

## 第 9 节验收标准

- [ ] `router.md` 存在且权限正确（edit: deny, bash: deny, webfetch: deny）
- [ ] `supervisor.md` 存在且权限正确（edit: deny, bash: deny, webfetch: deny）
- [ ] `specs/multi-agent-routing.md` 文档存在
- [ ] 能用样例任务验证路由判断：
  - 「采集本周 GitHub Trending」→ `collect` → `collector`
  - 「分析 raw 数据的质量」→ `analyze` → `analyzer`
  - 「把这批结果保存成知识条目」→ `organize` → `organizer`
  - 「审核一下 articles 目录的质量」→ `review` → `supervisor`
  - 「帮我写一个前端页面」→ `unknown` → `ask_human`
- [ ] Supervisor 能指出至少 3 类质量问题：字段缺失、标签宽泛、空洞词、评分异常、来源存疑

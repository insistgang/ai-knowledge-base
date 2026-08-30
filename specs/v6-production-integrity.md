# V6 生产工作流与语料完整性规格

## 1. 目标

让每日自动采集真正经过 LangGraph 审核链路，并在不删除历史 JSON 的前提下，
为 MCP 与 Dashboard 提供去重后的有效知识视图。

## 2. 范围

- 修通 `analyzed_items → analyses → revise → analyzed_items` 状态链。
- 让 GitHub Actions 调用 `pipeline.workflow_runner`，而不是线性流水线入口。
- 在工作流中继续记录并保存 LLM 成本指标。
- LLM 审核真实完成后将新条目标记为 `reviewed`；降级放行时保持 `draft`。
- MCP 与 Dashboard 按规范化 `source_url` 选择最新一条作为 canonical 记录。
- 修复已有重复 ID，并增加全库 ID 审计。
- 默认测试排除付费 `slow` 用例和 `v4-production/` 镜像目录。

## 3. 非破坏性原则

- 不删除现有 `knowledge/articles/*.json`。
- 历史重复 URL 仍保留为审计记录，只从默认查询视图中折叠。
- canonical 选择规则为：同一规范化 URL 保留 `collected_at` 最新的记录。
- 无 URL 的记录按 ID 保留；URL 与 ID 都缺失时按输入位置保留。

## 4. 生产工作流

```text
plan → collect → analyze → review ─┬→ organize → supervise → save
                                   ├→ revise → review
                                   └→ human_flag
```

- `analyze` 必须同时写入按来源分组的 `analyzed_items` 和扁平 `analyses`。
- `revise` 返回的条目数必须与原分析一致，随后按原来源边界回写。
- `review` 必须读取状态中的 provider，并记录调用成本。
- `save` 必须保存 raw、article 和 cost metrics。
- `dry_run` 不得写文章、指标或待人工审核文件。

## 5. 验收标准

- `python -m pytest` 默认只运行本地主测试目录且不调用付费 API。
- 工作流集成测试证明 Reviewer 收到非空 analyses。
- 修订后的 analyses 会进入最终 article。
- GitHub Actions 使用 Python 3.12 和 LangGraph runner。
- 全库 ID 唯一；历史重复 URL 由审计工具报告但不导致数据删除。
- MCP 的 `knowledge_stats` 同时报告原始条数、canonical 条数和隐藏重复数。
- Dashboard 默认展示 canonical 条目。

## 6. 暂不实施

- 删除或移动历史重复文件。
- 自动将全部历史 `draft` 批量改为 `reviewed`。
- HN、arXiv、RSS 新采集器。
- Docker 与 OpenClaw 工作区打包。

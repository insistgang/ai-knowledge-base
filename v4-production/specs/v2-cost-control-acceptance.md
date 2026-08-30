# V2 成本控制验收记录

## 1. 目标

第 8 节目标是让 AI 知识库 pipeline 从“能自动运行”升级为“成本可观测、预算可控、模型可路由”。

V2 不追求复杂调度，先保证每天自动采集时可以回答三个问题：

- 这次调用了多少次 LLM？
- 花了多少 token 和预估成本？
- 普通任务和深度任务分别使用哪个模型？

## 2. 已完成能力

- Token 统计：记录 `prompt_tokens`、`completion_tokens`、`total_tokens`。
- 成本估算：基于 `pipeline/model_client.py` 中的模型价格表估算 USD 成本。
- 成本落盘：每次 pipeline 运行生成 `knowledge/metrics/cost-YYYY-MM-DD.json`。
- 每日预算：默认 `AI_KB_DAILY_BUDGET_USD=0.10`。
- 超预算保护：累计成本达到预算后，后续条目自动走 `analyze_fallback()`。
- 模型路由：
  - 普通分析：`deepseek-v4-flash`
  - 深度分析：`deepseek-v4-pro`
- Dashboard 展示：显示 LLM 调用次数、token、预估成本、预算剩余和模型成本分布。
- GitHub Actions 集成：每日自动采集时带上预算和模型路由配置。

## 3. 关键文件

- `pipeline/cost_tracker.py`：成本记录、汇总和预算状态。
- `pipeline/model_client.py`：模型调用、usage 解析、成本估算和 `model_override`。
- `pipeline/pipeline.py`：预算读取、模型路由、fallback 保护和 metrics 保存。
- `reports/generate_dashboard.py`：读取 `knowledge/metrics/cost-*.json` 并渲染成本指标。
- `.github/workflows/daily-collect.yml`：自动采集、成本控制、dashboard 发布。
- `tests/test_cost_tracker.py`：成本聚合与预算保护测试。
- `tests/test_model_routing.py`：普通/深度模型路由测试。
- `tests/test_dashboard_metrics.py`：dashboard 成本 metrics 读取测试。

## 4. 验收命令

```bash
.venv/bin/python -m py_compile reports/generate_dashboard.py pipeline/pipeline.py pipeline/model_client.py pipeline/cost_tracker.py
.venv/bin/python -m unittest discover -s tests
AI_KB_DAILY_BUDGET_USD=0 .venv/bin/python pipeline/pipeline.py --sources github --limit 1 --dry-run --verbose
AI_KB_DAILY_BUDGET_USD=0 .venv/bin/python pipeline/pipeline.py --sources github --limit 1 --dry-run --analysis-depth deep
.venv/bin/python reports/generate_dashboard.py --verbose
git diff --check
```

## 5. 验收结果

- 单元测试通过：成本统计、预算状态、模型路由、dashboard metrics 读取均通过。
- dry-run 预算保护通过：`AI_KB_DAILY_BUDGET_USD=0` 时不调用 LLM，直接 fallback。
- dry-run 写入保护通过：`--dry-run` 不写 raw、articles、metrics 文件。
- 模型路由通过：
  - `--analysis-depth normal` 输出 `deepseek-v4-flash`
  - `--analysis-depth deep` 输出 `deepseek-v4-pro`
- Dashboard 生成通过：无成本文件时显示 0 和“暂无成本记录”；有成本文件时可展示真实成本。
- GitHub Actions 手动运行后可发布 Pages dashboard。

2026-04-30 GitHub Actions 实际成本记录：

- 模型：`deepseek-v4-flash`
- 调用次数：5
- prompt tokens：1338
- completion tokens：1508
- total tokens：2846
- 预估成本：`$0.00202006`
- 每日预算：`$0.10`
- 预算剩余：`$0.09797994`
- 预算状态：未超支

## 6. 使用方式

默认自动采集使用普通分析：

```bash
python pipeline/pipeline.py --sources github --limit 5 --verbose
```

手动深度分析使用：

```bash
python pipeline/pipeline.py --sources github --limit 5 --analysis-depth deep --verbose
```

调整每日预算：

```bash
AI_KB_DAILY_BUDGET_USD=0.10 python pipeline/pipeline.py --sources github --limit 5 --verbose
```

## 7. 备注

- 本地如果看不到最新 `knowledge/metrics/cost-YYYY-MM-DD.json`，需要先执行 `git pull` 同步 GitHub Actions 自动提交的结果。
- 当前 V2 的成本估算依赖 provider 返回的 usage 字段；如果 provider 不返回 usage，成本会记录为 0。
- 当前深度分析入口已经具备模型路由能力，但还没有单独设计更长 prompt 或更复杂的审稿流程；这部分留到后续多 Agent 或 LangGraph 阶段扩展。

## 8. 下一步

进入第 9 节：多 Agent 模式。

下一节重点从“单条 pipeline”升级为“Router + Supervisor”：

- Router 判断任务应该交给哪个 Agent。
- Supervisor 负责调度、检查和收敛结果。
- 为后续 LangGraph 工作流打基础。

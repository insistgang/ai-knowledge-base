# AI Knowledge Base

个人 AI 技术知识库助手实操项目，用于按课程资料逐步练习 SDD、Memory、Sub-Agent、Skill、Hook、MCP、成本控制、多 Agent 模式、LangGraph 和生产级工程实践。

## 当前阶段

- 已创建项目骨架。
- 已写入 `AGENTS.md` 项目规范。
- 已写入 `specs/project-vision.md` 项目愿景。
- 已写入 `opencode.json`，通过 `DEEPSEEK_API_KEY` 环境变量连接 DeepSeek。
- 已接入 GitHub Actions 每日采集，并生成 `reports/dashboard.html` 可视化看板。
- 已开始第 8 节成本控制，pipeline 会输出 `knowledge/metrics/cost-YYYY-MM-DD.json`。

## Dashboard

生成本地看板:

```bash
python reports/generate_dashboard.py
```

打开 `reports/dashboard.html` 即可查看统计卡片、评分分布、标签筛选和知识条目列表。

GitHub Pages 访问地址:

```text
https://insistgang.github.io/ai-knowledge-base/
```

## Cost Metrics

每次 pipeline 运行会记录 LLM 调用次数、token 用量和预估成本:

```bash
python pipeline/pipeline.py --sources github --limit 5 --verbose
```

成本文件保存到 `knowledge/metrics/cost-YYYY-MM-DD.json`。

默认每日预算是 `$0.10`，可通过环境变量覆盖:

```bash
AI_KB_DAILY_BUDGET_USD=0.10 python pipeline/pipeline.py --sources github --limit 5 --verbose
```

当本次运行的累计预估成本达到预算后，pipeline 会停止继续调用 LLM，并自动使用 fallback 分析。

## 下一步

1. 用 `@collector` 真实采集 GitHub Trending AI 相关 Top 5。
2. 将采集结果保存到 `knowledge/raw/`。
3. 用 `@analyzer` 和 `@organizer` 跑通一条小规模数据链路。

详细推进清单见 `docs/learning-roadmap.md`。
# ai-knowledge-base

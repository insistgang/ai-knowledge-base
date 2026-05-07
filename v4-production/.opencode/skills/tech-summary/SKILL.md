---
name: tech-summary
description: 当需要对采集到的技术项目、AI 项目、GitHub 热门仓库进行摘要、亮点提炼、评分和标签建议时使用
allowed-tools: Read, Grep, Glob, WebFetch
---

# 技术分析与摘要 Skill

## 使用场景

- 对 `knowledge/raw/` 中的采集数据逐条深度分析
- 提炼技术亮点、适用人群和相关度评分
- 为整理 Agent 提供结构化的分析结论

## 执行步骤

1. 读取 `knowledge/raw/` 中最新的采集文件（按文件名日期排序）。
2. 逐条分析每个项目，必要时访问原始 URL 核对技术细节。
3. 为每条生成不超过 100 字的中文摘要。
4. 提取 2-3 个技术亮点（如架构设计、性能数据、创新点）。
5. 给出 1-10 分评分并附简短理由。
6. 给出 3-5 个标签建议和适用人群。
7. 输出分析结果 JSON。

## 评分标准

| 分数 | 含义 | 说明 |
|------|------|------|
| 9-10 | 改变格局 | 可能改变工作流、研究方向或技术生态，值得重点跟进 |
| 7-8  | 直接有帮助 | 对开发、研究或产品实践有直接帮助，值得进入知识库 |
| 5-6  | 值得了解 | 有价值但短期行动价值有限 |
| 1-4  | 可略过 | 相关性强、信息不足、重复或不建议收录 |

**硬约束**：每批分析中，9-10 分项目不超过总数的 15%（例：15 个项目中最多 2 个 9-10 分）。

## 输出格式

```json
{
  "source_file": "github-trending-2026-04-29.json",
  "skill": "tech-summary",
  "analyzed_at": "2026-04-29T12:00:00Z",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "中文摘要，不超过 100 字。",
      "tech_highlights": ["亮点1", "亮点2", "亮点3"],
      "relevance_score": 8,
      "score_reason": "与 AI Agent 工程化实践直接相关。",
      "suggested_tags": ["agent", "workflow", "open-source"],
      "audience": ["developer", "researcher"],
      "uncertainties": []
    }
  ]
}
```

## 注意事项

- 不编造性能数据、论文结论或项目能力。
- 对不确定信息写入 `uncertainties` 字段，标注待确认。
- 评分必须有区分度，不能全部集中在 7-8 分。
- 标签使用小写英文，多个标签用数组表示。
- 不写入文件以外的内容，不执行 Bash 命令。

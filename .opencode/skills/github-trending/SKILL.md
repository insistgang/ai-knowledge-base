---
name: github-trending
description: 当需要采集 GitHub 热门开源项目、AI 热门仓库、LLM/Agent 项目时使用
allowed-tools: Read, Grep, Glob, WebFetch
---

# GitHub Trending 采集 Skill

## 使用场景

- 采集本周/本月 AI 领域 GitHub Trending 开源项目
- 追踪 LLM、Agent、MCP 等相关仓库热度变化
- 为知识库提供原始 GitHub 动态数据源

## 执行步骤

1. 访问 `https://github.com/trending?since=weekly` 获取本周热门仓库列表。
2. 按 AI/LLM/Agent/机器学习 相关关键词筛选仓库（见过滤规则）。
3. 访问每个候选仓库首页，提取完整描述、语言、Topics、Star 数。
4. 按 stars this week 降序排列，取 Top 5-N。
5. 为每条生成不超过 80 字的中文摘要。
6. 输出 JSON 并保存到 `knowledge/raw/github-trending-YYYY-MM-DD.json`。

## 过滤规则

保留以下主题的相关仓库，排除无关项目：

- **包含**：LLM、Agent、RAG、MCP、Vector Database、Embedding、Fine-tuning、Prompt Engineering、Tool Use、Code Generation、AI Agent、Machine Learning、Deep Learning、Transformer
- **排除**：纯前端 UI 框架、游戏、加密货币、操作系统内核、与 AI 无关的开发工具
- 去重：同一项目多次出现以外观 stars 最高的为准

## 输出格式

保存路径：`knowledge/raw/github-trending-YYYY-MM-DD.json`

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-04-29T12:00:00Z",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "一句话中文摘要，不超过 80 字。",
      "stars": 12345,
      "language": "Python",
      "topics": ["llm", "agent", "mcp"]
    }
  ]
}
```

## 注意事项

- 所有数据必须来自真实 GitHub 页面，不得编造。
- 摘要使用中文，关键技术术语保留英文。
- `stars` 为 stars this week，不是累计 stars。
- 不写入任何文件以外的内容，不执行 Bash 命令。

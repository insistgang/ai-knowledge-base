# AI 知识库课程推进路线图

## 当前状态

- 资料目录: `/home/insistgang/agent`
- 实操项目: `/home/insistgang/ai-knowledge-base`
- OpenCode: 已安装并可运行，项目已配置 DeepSeek provider
- Git: 已初始化并完成第一版提交
- 模型 API Key: 已通过 DeepSeek API 与 OpenCode 最小连通测试

## 分阶段任务

| 阶段 | 对应资料 | 目标产物 | 状态 |
| --- | --- | --- | --- |
| 0. 环境准备 | 第 1 节 | Node、OpenCode、模型 Key、连通测试 | ✅ 已完成 |
| 1. Memory 工程 | 第 2 节 | `AGENTS.md`、项目骨架、Memory 验证 | ✅ 已通过 Memory 验证 |
| 2. Sub-Agent | 第 3 节 | `collector.md`、`analyzer.md`、`organizer.md` | ✅ 已通过角色触发自检 |
| 3. Skill 封装 | 第 4 节 | `.opencode/skills/*/SKILL.md`、V1 流程 | ✅ 已完成 V1 |
| 4. Hook 质量门 | 第 5 节 | JSON 校验脚本、质量评分脚本 | ✅ 已完成 |
| 5. MCP 与 Pipeline | 第 6 节 | 模型客户端、流水线、RSS、MCP Server | ✅ 已完成 |
| 6. CI/CD 定时任务 | 第 7 节 | GitHub Actions、本地定时任务、Dashboard | ✅ 已完成 |
| 7. 成本控制 V2 | 第 8 节 | Token 统计、模型路由、V2 提交 | ✅ 已完成 V2 验收 |
| 8. 多 Agent 模式 | 第 9 节 | Router、Supervisor | ✅ 已完成 V3 多 Agent 验收 |
| 9. LangGraph 工作流 | 第 10 节 | `KBState`、5 节点工作流、审核循环 | ✅ 已完成 V4 LangGraph 验收 |
| 10. 自主规划 | 第 11 节 | Reviewer、Reviser、HumanFlag、Planner | ✅ 已完成（含 9 节点工作流） |
| 11. 生产级实践 V3 | 第 12 节 | CostGuard、Eval、安全检查、V3 提交 | ✅ 已完成 V6 生产完整性 |
| 12. 数据源扩展 | 第 13+ 节 | RSS、HN、arXiv 多源采集 | 🔄 规划中 |
| 13. 推送渠道 | 第 13+ 节 | Telegram Bot、飞书推送 | 🔄 V4 原型 |

## 当前进度

- **测试**：120+ 测试通过（含 LangGraph 集成测试需 `langgraph` 依赖）
- **知识数据**：625 篇历史 JSON，129 条有效 canonical 记录
- **成本指标**：122 个每日成本文件
- **待审核**：23 个 flag 文件
- **公众号文章**：10 篇课程文章 + 41 张配图（`content/wechat/yanlu-liangang/`）

## 下一步执行

1. 扩展数据源：RSS → Hacker News → arXiv。
2. 建立 `draft → reviewed → published` 人工审核流程。
3. 统一标签大小写和主题分类体系。
4. 决定是否将 Telegram 日报作为正式输出渠道。

## API Key 配置示例

```bash
echo 'export DEEPSEEK_API_KEY="sk-你的key"' >> ~/.bashrc
source ~/.bashrc
```

验证时只检查是否存在，不要把 Key 打印到聊天或日志里。

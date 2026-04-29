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
| 0. 环境准备 | 第 1 节 | Node、OpenCode、模型 Key、连通测试 | 已完成 |
| 1. Memory 工程 | 第 2 节 | `AGENTS.md`、项目骨架、Memory 验证 | 已通过 Memory 验证 |
| 2. Sub-Agent | 第 3 节 | `collector.md`、`analyzer.md`、`organizer.md` | 已通过角色触发自检 |
| 3. Skill 封装 | 第 4 节 | `.opencode/skills/*/SKILL.md`、V1 流程 | 已完成 V1 |
| 4. Hook 质量门 | 第 5 节 | JSON 校验脚本、质量评分脚本 | 进行中：JSON 校验完成 |
| 5. MCP 与 Pipeline | 第 6 节 | 模型客户端、流水线、RSS、MCP Server | 待做 |
| 6. CI/CD 定时任务 | 第 7 节 | GitHub Actions、本地定时任务 | 待做 |
| 7. 成本控制 V2 | 第 8 节 | Token 统计、模型路由、V2 提交 | 待做 |
| 8. 多 Agent 模式 | 第 9 节 | Router、Supervisor | 待做 |
| 9. LangGraph 工作流 | 第 10 节 | `KBState`、5 节点工作流、审核循环 | 待做 |
| 10. 自主规划 | 第 11 节 | Reviewer、Reviser、HumanFlag、Planner | 待做 |
| 11. 生产级实践 V3 | 第 12 节 | CostGuard、Eval、安全检查、V3 提交 | 待做 |

## 下一步执行

1. 创建 `hooks/check_quality.py` 质量评分脚本。
2. 对 `knowledge/articles/*.json` 输出 A/B/C 质量报告。
3. 手动模拟一次“产出 -> 校验 -> 修正 -> 再校验”的反馈循环。

## API Key 配置示例

```bash
echo 'export DEEPSEEK_API_KEY="sk-你的key"' >> ~/.bashrc
source ~/.bashrc
```

验证时只检查是否存在，不要把 Key 打印到聊天或日志里。

# Sub-Agent 测试日志

测试日期: 2026-04-29

## 测试环境

- 项目目录: `/home/insistgang/ai-knowledge-base`
- OpenCode: `1.14.29`
- 模型: `deepseek/deepseek-v4-flash`
- Provider: `deepseek`
- 配置文件: `opencode.json`

## 前置验证

### DeepSeek API 连通

已用最小 `curl` 请求验证 DeepSeek API 可用，模型返回 `OK`。

### OpenCode 连通

已用 `opencode run` 验证项目 provider 配置可用，模型返回 `OK`。

### Memory 加载

命令:

```bash
opencode run --model deepseek/deepseek-v4-flash "请根据当前项目的 AGENTS.md，简要回答这个项目的技术栈和编码规范。"
```

结果:

- OpenCode 明确执行了 `Read AGENTS.md`。
- 返回内容包含 Python 3.12、LangGraph、OpenCode/Codex、pytest、Git。
- 返回内容包含 PEP 8、snake_case、PascalCase、Google 风格 docstring、禁止裸 `print()`、禁止 `import *`。

结论: Memory 验证通过。

## Agent 识别与权限

`opencode agent list` 能识别以下自定义 Agent:

- `collector (subagent)`
- `analyzer (subagent)`
- `organizer (subagent)`

权限检查:

| Agent | edit | bash | webfetch | 结论 |
| --- | --- | --- | --- | --- |
| collector | deny | deny | allow | 符合采集 Agent 只搜不写的设计 |
| analyzer | deny | deny | allow | 符合分析 Agent 读源核验但不落盘的设计 |
| organizer | allow | deny | deny | 符合整理 Agent 写入项目文件但不访问外部网页的设计 |

## 触发测试

### collector

触发方式:

```text
@collector 角色自检：读取你的角色定义，返回 JSON：agent、mode、can_write、can_bash、can_webfetch、one_sentence_duty。不要写文件，不要访问网页。
```

结果摘要:

```json
{
  "agent": "collector",
  "mode": "subagent",
  "can_write": false,
  "can_bash": false,
  "can_webfetch": true
}
```

结论: 通过。

### analyzer

触发方式:

```text
@analyzer 角色自检：读取你的角色定义，返回 JSON：agent、mode、can_write、can_bash、can_webfetch、one_sentence_duty。不要写文件，不要访问网页。
```

结果摘要:

```json
{
  "agent": "analyzer",
  "mode": "subagent",
  "can_write": false,
  "can_bash": false,
  "can_webfetch": true
}
```

结论: 通过。

### organizer

触发方式:

```text
@organizer 角色自检：读取你的角色定义，返回 JSON：agent、mode、can_write、can_bash、can_webfetch、one_sentence_duty。不要写文件，不要访问网页。
```

结果摘要:

```json
{
  "agent": "organizer",
  "mode": "subagent",
  "can_write": true,
  "can_bash": false,
  "can_webfetch": false
}
```

结论: 通过。

## 发现的问题

- `opencode run --agent collector` 不能直接启动 subagent，会回退到默认 `build` agent。
- 正确触发方式是课程中的 `@collector` / `@analyzer` / `@organizer` mention。
- 纯 Markdown 角色文件会被识别，但不会绑定新版 OpenCode 权限；需要 YAML frontmatter。

## 调整记录

- 为三个 Agent 补充 YAML frontmatter。
- 设置 `mode: subagent`。
- 设置 `permission.edit`、`permission.bash`、`permission.webfetch`。

## 下一步

用 `@collector` 执行一次真实采集，先限制为 GitHub Trending AI 相关 Top 5，主 Agent 再把结果保存到 `knowledge/raw/`。


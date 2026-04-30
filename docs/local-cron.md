# 本地定时任务

第 7 节实操 2 的本地 cron 方案。GitHub Actions 已经能定时运行，本地 cron 是备选方案。

## 前置条件

- 项目目录: `/home/insistgang/ai-knowledge-base`
- 本地 `.env` 已配置 `DEEPSEEK_API_KEY`
- `.venv` 已安装 `requirements.txt`

## 手动测试

先用 dry-run 测脚本是否能启动:

```bash
cd /home/insistgang/ai-knowledge-base
AI_KB_DRY_RUN=1 AI_KB_LIMIT=1 scripts/run_local_collect.sh
tail -80 logs/local-collect.log
```

真实运行:

```bash
cd /home/insistgang/ai-knowledge-base
scripts/run_local_collect.sh
tail -80 logs/local-collect.log
```

## crontab 配置

编辑 crontab:

```bash
crontab -e
```

每天早上 8 点运行:

```cron
# AI Knowledge Base - local daily collection
0 8 * * * /home/insistgang/ai-knowledge-base/scripts/run_local_collect.sh
```

验证:

```bash
crontab -l
```

## 注意

- WSL 里的 cron 只有在 WSL/cron 服务运行时才会触发。
- 本地日志写入 `logs/local-collect.log`，该日志不会提交到 Git。
- 如需临时降低成本，可在 crontab 前加环境变量，例如 `AI_KB_LIMIT=1`。

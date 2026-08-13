# V5 采集质量与去重验收规格

## 1. 目标

修复每日 GitHub 采集长期重复相同高 star 项目的问题，在不删除历史知识条目、
不改变现有知识条目 JSON 格式的前提下，提高每日新增内容的多样性，并减少无效
LLM Token 消耗。

用户已于 2026-08-13 确认按以下优先级实施：

1. P0：在 LLM 分析前按历史 `source_url` 去重。
2. P0：让同一周的多个 GitHub Search 查询均衡贡献候选项目。
3. P1：优先采集近期仍活跃的项目。
4. P1：限制发送给模型的超长项目描述。

P2 人工审核状态流不属于本次改动。

## 2. 技术栈

- Python 3.12
- GitHub Search REST API
- JSON 知识条目
- pytest / unittest 风格测试

## 3. 实现范围

- `pipeline/pipeline.py`
  - 读取历史文章的 `source_url`。
  - 规范化 URL 后过滤历史项目和本次运行内的重复项目。
  - 对本周的四个查询结果进行轮询选取。
  - 给查询追加最近 90 天有 push 的限定条件。
  - 将送入模型的 description 截断到 1,200 字符。
- `tests/test_collection_quality.py`
  - 覆盖 URL 规范化、历史读取、均衡取样、查询条件和 prompt 截断。
- `v4-production/`
  - 保持生产快照中的实现和测试与根目录一致。

## 4. 代码风格

核心转换逻辑保持为可独立测试的纯函数，网络请求和文件读取只留在边界函数中：

```python
selected = select_balanced_repositories(
    candidate_groups,
    limit=5,
    excluded_urls=existing_urls,
)
```

- 函数和变量使用 `snake_case`。
- 业务函数使用 Google 风格 docstring。
- 使用 `logging`，不在应用代码中新增裸 `print()`。
- 不新增第三方依赖。

## 5. 测试策略

先写失败测试，再实现最小代码使其通过：

```bash
uv run --python 3.12 --with pytest --with-requirements requirements.txt \
  python -m pytest tests/test_collection_quality.py

uv run --python 3.12 --with pytest --with-requirements requirements.txt \
  python -m pytest tests

uv run --python 3.12 --with pytest --with-requirements ../requirements.txt \
  python -m pytest tests/test_collection_quality.py \
  tests/test_cost_tracker.py tests/test_model_client.py tests/test_model_routing.py

git diff --check
```

GitHub API 在单元测试中使用 stub，不消耗真实 API 配额；完成后使用零预算 dry-run
验证真实候选过滤，避免调用 LLM 和写入知识文件。

## 6. 边界

### 始终执行

- 在调用 LLM 前完成历史去重。
- 保留原始采集描述，截断只发生在模型输入边界。
- 单个损坏的历史 JSON 只记录警告，不阻塞整次采集。
- 保持每日最大产出数量由现有 `--limit` 控制。

### 需要另行确认

- 删除或合并现有的重复历史条目。
- 修改知识条目的状态流或批量把 `draft` 改成其他状态。
- 增加新的外部数据源或依赖。

### 禁止执行

- 删除历史知识文件。
- 把 API Key、Token 或完整模型响应写入仓库。
- 为了补足数量而重新选择历史中已有的 `source_url`。

## 7. 验收标准

- 历史 `source_url` 即使大小写或结尾 `/` 不同，也不会再次进入分析队列。
- 一次运行内出现的相同 URL 只保留一次。
- 四个查询均成功且均有候选时，前四个入选项目分别来自四个查询。
- 某个查询没有新候选时，其他查询可以继续补足到 `limit`。
- GitHub 查询包含 `pushed:>=<最近 90 天日期>`。
- 每个查询最多读取足够的候选池，而不是第一条查询拿满后停止请求。
- 模型输入中的项目 description 不超过 1,200 字符，raw 保存内容不受影响。
- 相关测试、根目录完整测试和格式检查通过。
- 不产生新的知识文件或成本记录作为测试副作用。

## 8. 已知取舍

- 本次采用“历史永久去重”。项目有重大更新时仍不会自动再次入库；以后可以增加
  `source_url + release/version` 的更新型条目策略。
- 近期活跃以 GitHub `pushed_at` 为准，默认窗口为 90 天，不等同于真正的
  GitHub Trending 排名。
- 如果所有候选都已存在，允许当天少于 5 条，优先保证质量而不是凑数。

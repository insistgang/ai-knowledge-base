# V4 LangGraph 工作流验收总结

## 第 10 节目标

将线性 pipeline 升级为基于 **KBState**、五个节点函数、条件边和 **LangGraph** 的状态机工作流。每个节点是纯函数 `(KBState) → KBState`，条件路由决定下一步走向，Supervisor 在入库前把关。

## 新增/修改文件

| 文件 | 说明 |
|------|------|
| `requirements.txt` | 新增 `langgraph>=0.2` 依赖 |
| `pipeline/workflow_state.py` | 定义 `KBState` TypedDict 和 `create_initial_state` |
| `pipeline/workflow_nodes.py` | 5 个节点函数：collect / analyze / organize / supervise / save |
| `pipeline/workflow_routes.py` | 3 个条件路由函数：after_collect / after_analyze / after_supervisor |
| `pipeline/workflow_graph.py` | `build_workflow_graph()` 构建 LangGraph StateGraph |
| `pipeline/workflow_runner.py` | `run_workflow()` 一行启动完整工作流 |
| `tests/test_workflow_state.py` | KBState 默认值与引用隔离测试 |
| `tests/test_workflow_nodes.py` | 5 个节点行为测试 |
| `tests/test_workflow_routes.py` | 条件路由测试 |
| `tests/test_workflow_graph.py` | 图构建与依赖错误测试 |
| `tests/test_workflow_runner.py` | 运行入口委托测试 |

## 测试结果

```text
$ python -m unittest tests/test_workflow_state.py
Ran 25 tests  OK

$ python -m unittest tests/test_workflow_nodes.py
Ran 13 tests  OK

$ python -m unittest tests/test_workflow_routes.py
Ran 13 tests  OK

$ python -m unittest tests/test_workflow_graph.py
Ran 5 tests   OK

$ python -m unittest tests/test_workflow_runner.py
Ran 4 tests   OK

$ python -m unittest discover -s tests
Ran 88 tests  OK
```

## 工作流结构

```
                 ┌─────────────┐
                 │   collect   │
                 └──────┬──────┘
               ┌────────┼────────┐
               │ error/empty      │ data present
               ▼                  ▼
         supervise             analyze
         ┌───┴───┐           ┌──┼──────┐
         │ error/empty        │ error   │ data present
         ▼                     ▼         ▼
      [STOP]              supervise   organize
                                 │
                                 ▼
                            supervise
                    pass ───┼── needs_revision ──► [END]
                            │── blocked ─────────► [END]
                            │── unknown ─────────► [END]
                            │
                            ▼
                           save ─► [END]
```

### 路由规则

| 节点 | 条件 | 下一节点 |
|------|------|---------|
| collect | 有数据且无错误 | analyze |
| collect | 无数据或有错误 | supervise |
| analyze | 有数据且无错误 | organize |
| analyze | 无数据或有错误 | supervise |
| organize | — | supervise |
| supervise | review_status=pass | save |
| supervise | review_status=needs_revision | END |
| supervise | review_status=blocked | END |
| save | — | END |

## 验收结论

- [x] KBState 已完成，25 个测试覆盖
- [x] 5 个节点已完成，13 个测试覆盖
- [x] 条件路由已完成，13 个测试覆盖
- [x] LangGraph 图已完成，5 个测试覆盖
- [x] run_workflow 入口已完成，4 个测试覆盖
- [x] 全量测试 88 通过
- [x] **可以进入第 11 节自主规划 / Reviewer / Reviser / HumanFlag**

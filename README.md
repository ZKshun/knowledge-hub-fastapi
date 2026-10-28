# Knowledge Hub · FastAPI

企业级 RAG 知识库服务端的 Python + FastAPI 重构项目。按原项目 `v1`–`v21` 的功能边界递进实现，严格保留接口契约和 PostgreSQL、MongoDB、Elasticsearch、Neo4j、Redis、RabbitMQ、RustFS 的职责。

目标是让接手工程师和新会话中的 Coding Agent 都能清楚理解业务、定位代码、运行验证并继续上一阶段工作。

## 当前状态

已完成 **v1 Task1–4**：原版基线、领域/配置/门禁、双库读取/迁移/锁/日志，以及创建/查询用例和可恢复创建。审查发现的BIGINT兼容问题已修复并回归；75份原版快照保留，当前完整 **172项通过、无跳过**。下一项Task5：修改/删除与完整恢复；FastAPI接口和完整验收仍待Task6–7。业务闭环图描述最终目标，不表示全部功能已可用。

新会话从 [AGENTS.md](AGENTS.md) 开始，随后读取 [当前进度与下一步](docs/refactor/status.md) 和 [开发 SOP](docs/refactor/agent-sop.md)。

## 完整业务闭环

```text
用户、角色、权限、团队
          ↓
创建文档 / 上传文件 / MinerU 解析
          ↓
PostgreSQL 元数据 + MongoDB 正文 + RustFS 附件
          ↓
草稿 → 提交审核 → 通过发布 / 驳回 → 归档 / 删除
          ↓
RabbitMQ 异步知识处理
          ├── 文档全文 → Elasticsearch kh_document
          ├── 分块 + Embedding → Elasticsearch kh_chunk
          └── 实体关系抽取 → Neo4j
          ↓
全文搜索 + BM25/向量混合检索 + Rerank + GraphRAG
          ↓
普通问答 / 流式问答 / Agentic RAG / 联网搜索
          ↓
会话、短期记忆、长期记忆、引用、评测和链路观测
          ↓
分类、版本、评论、点赞、收藏、分享、通知
```

贯穿全流程：认证、RBAC、团队范围、文档可见性、跨库一致性、异步幂等、错误处理和可观测性。流程中后期出现的权限和评测能力，其扩展边界从 v1 设计；具体功能按版本交付。

## 开发与版本

每版执行以下循环，两个版本之间必须完成合并：

```text
main → 派生 v1 → 实现/测试/验收 → 合并 main
main → 派生 v2 → 实现/测试/验收 → 合并 main
main → 派生 v3 → …
```

`vN` 是开发里程碑分支，不是 HTTP API 版本；不得因此把 `/documents` 改成 `/api/vN/documents`。

Python 仓库位于本目录；同级 `../knowledge-hub-backend` 与 `../knowledge-hub-frontend` 是参考系统。完整依据和固定提交见 [源系统盘点](docs/refactor/source-inventory.md)。

## 文档导航

| 想了解 | 文档 |
| --- | --- |
| 任务目标、范围和方案 | [总体设计](docs/refactor/design.md) |
| 下一步做什么、什么还没做 | [当前状态](docs/refactor/status.md) |
| 各版本功能与验收出口 | [v1–v21 路线图](docs/refactor/roadmap.md) |
| 代码存在哪里、怎样依赖 | [架构与目录](docs/refactor/architecture.md) |
| 命名、排版、类型和文件行数 | [代码规范](docs/refactor/code-standards.md) |
| 接口、数据、MQ、流式如何兼容 | [兼容策略](docs/refactor/compatibility.md)、[契约入口](docs/contracts/README.md) |
| Agent 开发、验证、恢复和交接 | [开发 SOP](docs/refactor/agent-sop.md) |
| 已确认的规则及其来源 | [决策记录](docs/refactor/decisions.md) |
| v1 的具体工作 | [规格](docs/versions/v1/spec.md)、[实施计划](docs/superpowers/plans/2026-10-28-v1.md) |
| 本阶段做了哪些需求、如何完成 | [Task 4 需求与实现报告](docs/versions/v1/task-4-report.md)、[Task 3](docs/versions/v1/task-3-report.md)、[Task 2](docs/versions/v1/task-2-report.md)、[Task 1](docs/versions/v1/task-1-report.md) |
| 历次工作与证据 | [工作日志](docs/refactor/work-log.md) |

## 运行与验证

已采用 Python 3.12、uv，并在 `uv.lock` 锁定 FastAPI、Pydantic、SQLAlchemy Async、Alembic、PyMongo 等依赖。安装和现有测试：

```bash
uv sync --locked --all-groups --link-mode=copy
uv run --locked pytest tests/unit tests/contract -q
uv run --locked ruff format --check .
uv run --locked ruff check scripts tests src
uv run --locked mypy src scripts migrations tests/contract/comparison.py
uv run --locked python scripts/check_file_limits.py
```

Windows 当前主机临时目录有账户权限差异时，按 [基线复现](docs/versions/v1/contract-baseline.md) 指定项目内独立 `--basetemp`。真实数据库探针测试需要专用测试容器和显式环境开关；完整已验证结果见阶段报告。

真实数据库验证使用`KH_RUN_STORAGE_DB_TESTS=1`，旧库探针使用`KH_RUN_LEGACY_DB_TESTS=1`；两个开关均启用并启动专用容器时，本轮完整172项通过。隔离/复现命令见[Task3报告](docs/versions/v1/task-3-report.md)，创建恢复协议、BIGINT语义和故障验证边界见[Task4报告](docs/versions/v1/task-4-report.md)。不要把未启用数据库测试的快速检查当作v1验收。

当前没有 Python HTTP 服务启动命令；旧 NestJS 的隔离构建、采集、测试和停止步骤见 [契约基线复现](docs/versions/v1/contract-baseline.md)。后续服务命令必须在对应实现完成并实测后补齐。

配置保留旧 `POSTGRES_*`、`MONGO_URI`、`SNOWFLAKE_*`、`PORT` 名称，见 [.env.example](.env.example)。显式调用 `Settings()` 时读取进程环境；需要 dotenv 时显式传 `Settings(_env_file=...)`。模块导入不读取配置、不建立连接。默认端口 8000；连接值是开发占位。每个活动进程须分配唯一 worker ID，并共享相同 epoch；进程内共享同一生成器。时间回拨或单毫秒超过 4096 个 ID 时明确失败，部署与重试说明见 [阶段报告](docs/versions/v1/task-2-report.md)。

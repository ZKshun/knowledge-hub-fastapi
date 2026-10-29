# Knowledge Hub · FastAPI

企业级 RAG 知识库服务端的 Python + FastAPI 重构项目。按原项目 `v1`–`v21` 的功能边界递进实现，严格保留接口契约和 PostgreSQL、MongoDB、Elasticsearch、Neo4j、Redis、RabbitMQ、RustFS 的职责。

目标是让接手工程师和新会话中的 Coding Agent 都能清楚理解业务、定位代码、运行验证并继续上一阶段工作。

## 当前状态

已完成 **v1 Task1–6**，Task7正在验收：五个FastAPI文档接口、双库存储与恢复、生命周期、协议适配和请求日志。原75份HTTP/双库证据重放通过；另补65份原版传输证据和1份SQL文本编码证据。独立审查3项问题经同轮修复。Task7的新依赖环境与全新双库完整 **445项通过、0跳过，覆盖94.85%**；本地合并状态以[当前进度](docs/refactor/status.md)为准。业务闭环图描述最终目标，不表示后续版本功能已可用。

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
| 本阶段做了哪些需求、如何完成 | [Task 6 需求与实现报告](docs/versions/v1/task-6-report.md)、[Task 5](docs/versions/v1/task-5-report.md)、[Task 4](docs/versions/v1/task-4-report.md)、[Task 3](docs/versions/v1/task-3-report.md)、[Task 2](docs/versions/v1/task-2-report.md)、[Task 1](docs/versions/v1/task-1-report.md) |
| v1 全部需求如何实现、如何验收 | [v1 验收记录](docs/versions/v1/acceptance.md) |
| 历次工作与证据 | [工作日志](docs/refactor/work-log.md) |

## 本地运行与验证

需 Python 3.12、uv 和 Docker Compose。以下 PowerShell 步骤只使用`kh-fastapi-v1-test`专用容器、回环端口55432/57017和合成数据；先确认端口未被其他服务占用。旧版PostgreSQL表由[已核验原版SQL夹具](tests/fixtures/legacy_v1/postgresql/init.sql)在新测试卷初始化，用于契约比较；正式FastAPI运行另建空数据库：

```powershell
uv sync --locked --all-groups --link-mode=copy
docker compose -p kh-fastapi-v1-test -f deploy/compose.test.yml up -d --wait
docker compose -p kh-fastapi-v1-test -f deploy/compose.test.yml exec -T postgres psql -U kh_test -d postgres -c 'CREATE DATABASE knowledge_hub_fastapi_app_test'
@'
PORT=38121
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
POSTGRES_USER=kh_test
POSTGRES_PASSWORD=local-contract-only
POSTGRES_DB=knowledge_hub_fastapi_app_test
MONGO_URI=mongodb://127.0.0.1:57017/knowledge_hub_fastapi_app_test
SNOWFLAKE_WORKER_ID=33
SNOWFLAKE_OFFSET=1704067200000
'@ | Set-Content .env.local -Encoding ascii
uv run --locked --env-file .env.local alembic upgrade head
uv run --locked python scripts/init_mongo_indexes.py --env-file .env.local
uv run --locked python scripts/recover_document_operations.py --env-file .env.local --limit 100
uv run --locked python -m knowledge_hub.main --env-file .env.local
```

此处`CREATE DATABASE`仅对新测试卷执行一次；再次运行应使用已有的专用库，不能在有业务数据的库上盲目重建。服务默认绑定127.0.0.1；示例监听38121，`GET /docs`与`GET /openapi.json`可检查接口，五个业务路径是`POST/GET /documents`和`GET/PATCH/DELETE /documents/{id}`。本轮已按此顺序对另一个全新验收Compose项目实测：迁移升级→降级→升级、索引初始化两次、恢复计数全0、正式模块启动及五接口HTTP与两库状态关联。默认PORT为8000；`knowledge_hub.main:app`可作为ASGI入口。启动只检查连接，不自动迁移、初始化索引或恢复；已有无版本业务表会明确拒绝迁移。

恢复命令输出`completed/compensated/failed`计数；failed>0退出1，配置/连接异常退出2。支持`--schema`、`--collection`指定资源；真实故障与重试演练见[Task5报告](docs/versions/v1/task-5-report.md)。内部创建标记不会被自动清除。

完整质量门禁与原版差分使用同一批专用容器：

```powershell
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src scripts migrations tests/contract/comparison.py
uv run --locked python scripts/check_file_limits.py
$env:KH_RUN_STORAGE_DB_TESTS='1'
$env:KH_RUN_LEGACY_DB_TESTS='1'
uv run --locked pytest tests/unit tests/integration tests/contract tests/e2e -q --cov=knowledge_hub --cov-report=term-missing --cov-fail-under=85
docker compose -p kh-fastapi-v1-test -f deploy/compose.test.yml stop
```

Windows临时目录权限不同时给pytest增加新的项目内`--basetemp=.local/pytest-runs/<标识>`，先建父目录；不开两个DB开关会跳过真实库用例，不能算完整验收。[质量工作流](.github/workflows/quality.yml)复用这些命令，但当前Python仓库无remote，云端运行未发生。原版75项HTTP/双库证据、65项传输证据和文本编码证据已版本化，无需构建Nest服务即可重放；重新采集原版的隔离流程见[基线复现](docs/versions/v1/contract-baseline.md)。`stop`保留本项目测试卷和数据。

JSON与表单的展开正文上限是100KB；兼容gzip/deflate/br及UTF-8/16/32，失败按原400/413/415返回。请求日志只记录ID、方法、状态、耗时和异常类型。配置名称与占位示例见[.env.example](.env.example)，不会隐式读取本地.env；每个活动进程须分配唯一Snowflake worker ID并共享相同epoch，时间回拨或单毫秒超过4096个ID时明确失败，见[Task2报告](docs/versions/v1/task-2-report.md)。

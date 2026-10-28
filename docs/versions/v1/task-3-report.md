# v1 Task 3：需求与实现对照

日期：2026-10-28；分支：`v1`；开始前HEAD：`8befa08758b21dc80559d06c9441573378fa7fe2`。实现、验证与独立审查完成，最终提交由Git查询。没有验收或合并完整v1。

## 完成哪些需求、如何完成

| 需求 | 实现方式与关键位置 | 验证证据 |
| --- | --- | --- |
| 保持原PostgreSQL结构 | `migrations/versions/0001_documents.py`显式建表；`document_row.py`映射原23列，BIGINT/VARCHAR/SMALLINT/TIMESTAMP及默认值/可空性不变 | 迁移列型、默认值逐项与Task1真实public原表比较；唯一content_id与非空约束实测；空schema升级→降级→升级→再次升级 |
| 防止误覆盖已有库 | `migrations/env.py`在DDL前检查业务表与有效Alembic版本；无版本的已有表拒绝执行，不自动stamp；offline模式拒绝绕过检查 | 已有表含记录123，迁移明确报unversioned，记录仍在，alembic_version未创建 |
| 双库读取和分页 | `metadata_repository.py`只读SQL；`content_repository.py`读取原ObjectId/camelCase正文；`document_store.py`组合详情与分页 | 字符串大ID/外键、UTC时刻、null、软删除、缺正文空字符串；ILIKE、通配符、组合筛选、status999、分页计数与顺序；关闭Mongo后分页仍可用 |
| 复现BSON编码 | `mappers.py:bson_string/make_content_record`只在持久边界将未配对UTF-16代理字符替换为U+FFFD | 真实Mongo插入后读回，对比原版044快照，得到199个a+U+FFFD+...；正文长度206、version1不变 |
| 文档级跨步骤互斥 | `document_lock.py`独立连接持有session advisory lock；提交后仍持锁；取消/失败时释放或作废连接；默认锁等待5秒 | 同文档串行、不同文档并行、无需元数据行、跨独立事务提交仍阻塞、业务异常/持有者取消/等待者取消、等待超时及再次获取 |
| 避免连接池饥饿 | `PostgresDatabase`分离业务与锁连接池，store仅从lock_engine取锁连接；close释放两个池 | 20并发详情先稳定3秒超时，分池后通过；避免所有连接持锁后无法查询日志/元数据 |
| 持久恢复依据与事务边界 | `operation_types.py/operation_row.py/operation_journal.py`建立添加式`kh_document_operation`；prepare独立提交，mark_completed由调用者与元数据同事务提交 | 新连接看到prepared；业务回滚保留prepared且无元数据；业务提交后metadata/completed共同可见；未完成操作阻止详情；有界pending列表和同文档单一pending约束 |
| 索引可重复初始化 | `scripts/init_mongo_indexes.py`创建documentId唯一索引和deleted索引，遇到冲突报错，不自动删除旧索引/数据 | 调用两次通过；重复documentId被真实Mongo拒绝 |
| 清晰职责和质量 | 独立客户端、行模型、记录模型、映射、读取仓储、锁、日志、store；无网络全局实例；官方Pydantic mypy插件识别_env_file | 完整133测试无跳过；严格类型46文件；格式/lint通过；最长生产/脚本105行，均低于300 |

## 可供后续沿用的接口

- `PostgresDatabase(settings, schema="public")`提供engine、lock_engine、sessions，`await close()`释放两池；连接URL用结构化URL构建，密码不拼接，SQL参数隐藏。客户端创建不连库，显式请求时才I/O。
- `MongoDatabase(settings)`提供client/database，`await close()`释放客户端；AsyncMongoClient不跨事件循环共享。URI无数据库时保留驱动默认test，正式部署应显式指定数据库。
- `PostgresMongoDocumentStore(postgres, collection)`当前只有get/page；尚未作为完整DocumentStore注入HTTP，Task4/5再补create/mutate/soft_delete，不能加入成功假实现。
- `DocumentLock(postgres.lock_engine, timeout_ms=5000).acquire(document_id)`是async context manager，yield None。锁键是数值BIGINT文档ID，与行是否存在无关；不要改成事务级锁或用业务engine承载等待锁。
- `OperationRecord`含operation_id(UUID字符串)、document_id、operation_type、state、expected_version、snapshot(JSON对象)、last_error、created_at、updated_at；没有文档外键，允许创建前prepare。
- `OperationJournal(sessions).prepare(record)`独立持久提交；`get(operation_id)`、`has_pending(document_id)`、`list_pending(limit=100)`使用新session；`mark_completed(session, operation_id)`只更新调用者事务，不能自行commit。state与kind及expected_version有SQL约束；pending上限1000。
- Mongo `DocumentContentRecord`保持原字段，增加可选内部operationId；ContentSnapshot保留正文版本/操作标记。`make_content_record(document_id,content,now=...,summary=...,operation_id=...)`供Task4使用；内部标记不进入HTTP响应。
- 详情读取在锁内检查pending后读双库；当前pending显式抛DocumentOperationPending，不伪造正常详情。Task4–5负责恢复推进，Task6负责原错误适配。

## 工程取舍与后续风险

1. 沿用干净专属v1工作区；测试仅对已校验本机55432/57017的knowledge_hub_fastapi_test操作。新测试用kh_t3_UUID临时SQL schema、document_content_kh_t3_UUID临时Mongo集合，finally清理，不修改public表结构。完整回归中的既有legacy探针仍按其原流程重置专用public表/document_content的合成数据；原始75份快照不改。临时容器可用不等于在旧业务库上自动baseline。
2. 两个SQL池各默认5常驻+10溢出，连接上限合计30/应用进程，部署须计入进程数及数据库连接预算；迁移临时进程使用后也要close。此分离是并发测试证明必要的内部实现选择。
3. 业务表仍是TIMESTAMP without timezone，客户端会话显式UTC，读出映射为有时区UTC；内部操作表时间用TIMESTAMPTZ。不授权改旧列型或自动转换既有库时区。
4. 同文档最多一条prepared/compensation_pending，由SQL部分唯一索引兜底。恢复快照可含必要正文，只存受控数据库，不写普通日志；last_error仅允许后续协调器提供脱敏错误。
5. 获取新session锁不证明旧业务SQL事务已经结束。Task4/5必须结束/丢弃旧业务连接并核验事务结束，再核对completed/metadata；不能直接用异常或新锁结果删除Mongo。当前日志与锁单元不能代替COMMIT未知结果/重启恢复证据。
6. Alembic迁移是显式冻结的DDL，当前未提供autogenerate或既有库stamp流程；offline不能执行安全检测，因此明确拒绝。Mongo初始化遇到原有非唯一documentId索引冲突会失败，需单独评审迁移，不能静默drop/recreate。

实现核对了[SQLAlchemy Async官方文档](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html)、[PostgreSQL session advisory lock语义](https://www.postgresql.org/docs/17/functions-admin.html)、[PyMongo Async迁移说明](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)。兼容依据仍为固定NestJS v1源码和既有运行快照。

## 实际验证与复现

环境：Python3.12.14；PostgreSQL16测试容器、Mongo7测试容器；原HTTP服务未启动。只有专用测试服务执行up，未删除卷。静态门禁包括迁移代码。

```powershell
docker compose -p kh-fastapi-v1-test -f deploy/compose.test.yml up -d --wait
$env:KH_RUN_STORAGE_DB_TESTS='1'
$env:KH_RUN_LEGACY_DB_TESTS='1'
uv run --locked --link-mode=copy pytest -q --basetemp=.local/pytest-runs/<新的标识> --cov=knowledge_hub --cov-report=term-missing
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src scripts migrations
uv run --locked python scripts/check_file_limits.py
uv lock --check --offline
```

| 本轮命令/阶段 | 实际结果 |
| --- | --- |
| 开始前pytest | 113 passed / 1 skipped（旧库探针未开启） |
| Task3首轮TDD | 缺客户端模块导致失败；实现后18项真实数据库测试通过 |
| 并发连接池回归 | 20并发读取3秒超时RED → 分离锁池后GREEN |
| pytest全部，task3-all-007，两个环境开关均1 | **133 passed / 0 skipped / 0 failed**；生产语句+分支覆盖95.10% |
| ruff format --check . / ruff check . | 85 files already formatted / All checks passed |
| mypy src scripts migrations | strict，46 source files无问题；启用pydantic.mypy，未加宽泛ignore |
| check_file_limits.py | 44生产/脚本文件，最长105/300物理行 |
| uv lock --check --offline | 45 packages解析通过，依赖声明未漂移 |
| 交接文档复核 | 21个Markdown、88个本地链接、0失效/围栏错误；AGENTS保持30物理行 |

单次独立只读审查：**无Critical/Important/Minor**。reviewer核对暂存实现、测试与固定旧源码，自行执行Ruff、52文件格式、BSON孤立代理/代理对/截断边界及diff空白检查。133项真实完整回归、95.10%覆盖及mypy由主执行者运行，reviewer未重跑会写入数据库的测试，没有把未执行项归为reviewer证据。

执行者确认审查未验收边界：HTTP校验/错误与超大ID最终响应留Task6；写入、未知COMMIT、补偿/重启及并发版本保护留Task4–5；lifespan/E2E/CI留Task6–7。baseline/stamp/offline/autogenerate与手工非法状态/缺失Mongo必备字段的数据导入另行规划，当前拒绝或严格失败，不伪造兼容。漏做前述验证会造成数据或协议风险，完整v1不能据此验收。最终README/status/计划/日志由本次交接同步。

资源复核：临时SQL schema/Mongo集合均0残留；两个专用测试容器已停止并确认Exited(0)，卷保留。CLI --help与Alembic history已实测；尚未对已有业务库执行迁移。覆盖率只反映当前实现，不能验收尚未实现的恢复、HTTP或E2E。本阶段提交信息`feat(v1): add storage reads migrations and operation journal`，提交SHA由Git核验。

## 未完成与下一步

下一项Task4：基于本阶段锁、日志、读取仓储，实现创建与详情/分页用例、写入协调和恢复；随后Task5修改/删除、Task6五接口兼容、Task7完整验收/CI。v1保持implementing，不合并main或推送。

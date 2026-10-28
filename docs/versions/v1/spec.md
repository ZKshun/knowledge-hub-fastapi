# v1：文档与工程基线规格

总体方向已接受。来源：旧后端 `f9dfce20ffe798dc35ede0a74219f06bf3d6980f`；接口字段和副作用详见 [v1 契约](../../contracts/v1.md)。本版尚未开始实现。

## 目标与边界

交付能在隔离环境运行的文档 CRUD：创建→分页/详情→修改→软删除；PostgreSQL 元数据 + MongoDB 正文，生成字符串雪花 ID，保持原版字段和行为。

同时建立包管理、配置、生命周期、错误适配、迁移、测试隔离、质量门禁和恢复工具。v1 不包含文件上传、RabbitMQ、ES、Neo4j、模型、登录、审核或互动功能；这些按路线图交付。

## 固定工程选择

- Python 3.12；uv 管理并锁定依赖。
- FastAPI + Pydantic，SQLAlchemy Async + asyncpg，Alembic，PyMongo Async。
- pytest/HTTPX、Ruff、mypy strict；生产代码覆盖率至少 85%；单生产文件最多 300 物理行（含注释空行），目标 200。
- 本版模块名 documents；跨库恢复工具在此模块；内部操作日志作为添加式 PostgreSQL 表 `kh_document_operation`。
- Docker Compose 测试项目固定名 `kh-fastapi-v1-test`，数据库名 `knowledge_hub_fastapi_test`，连接配置显式传入；仅测试 PostgreSQL/MongoDB，禁止挂载旧 volumes。
- API 默认开发端口 8000，可配置 PORT；旧服务保持原端口用于差分。服务端路由不添加 `/api`。

精确依赖版本经安装验证写入 uv.lock，不在本文猜测未来版本。环境样例仅包含占位或开发测试配置，不含真实密钥。

## API 与核心类型

实现 [v1 契约](../../contracts/v1.md) 中五个 `/documents` 接口。外部保持 camelCase、字符串 ID、原分页封装和错误；POST 成功状态按原版运行结果固定，当前源码推导为 201。

内部 `Document` 为不可直接序列化的领域数据；`DocumentDetail` 组合 Document 与 content；`DocumentPage` 包含 items、total、page、page_size。`CreateDocumentCommand` 表达创建输入，`UpdateDocumentCommand` 使用 `changes` 字典保存显式提交字段，必须区分 null 与未传。纯变换返回 `DocumentMutation(target: DocumentDetail, provided_fields: frozenset[str])`，字段集合使用内部 snake_case，一直保留到持久化步骤。

显式提交 content 即使与原字符串相同，也要按原版递增 Mongo version；空 PATCH、仅 title 或仅 summary 不增版本。不能通过比较新旧正文是否相等来判断版本动作。

类型边界：`DocumentId` 为字符串 NewType；`DocumentFieldValue = str | int | bool | None`；changes 为 `Mapping[str, DocumentFieldValue]`；JSON/持久化映射在 API/infrastructure 中进行。领域对象不依赖 FastAPI、Pydantic 或 SQLAlchemy。

配置保留 POSTGRES_*、MONGO_URI、SNOWFLAKE_WORKER_ID、SNOWFLAKE_OFFSET、PORT 名称，新增测试/日志配置需在样例与 README 说明。worker ID 分配和时钟回拨策略必须测试，不能在生产多实例共用固定 worker ID。

## 持久化和一致性

Alembic 建立原版 `kh_document` 的兼容结构和内部操作日志，Mongo 初始化原集合及索引。空库迁移必须成功；已有旧库的 baseline/导入不在 v1 自动执行，须显式检测并拒绝静默覆盖。

创建、修改、软删除必须定义并记录跨库步骤：先准备操作日志，再执行 Mongo 写与 PostgreSQL 元数据事务，成功标记 completed；SQL 确认回滚后才恢复或删除 Mongo 变化。Mongo 变更与补偿以操作 ID/预期正文版本作条件，避免覆盖后续成功修改。

COMMIT 回包丢失属于结果未知，不得因客户端异常直接补偿。在线错误路径与重启恢复都要结束/丢弃旧连接、重新获取同文档锁，确认原事务已结束，再用新连接核验 completed/元数据。提交成功保留正文，确认未提交才补偿；无法核验时保留 prepared 等待恢复并阻止同文档新写入，数据库持续不可用时不猜测执行结果。

`kh_document_operation` 保存 operation_id、document_id、operation_type、state、expected_version、恢复快照、last_error（脱敏）、created_at、updated_at。恢复快照只存恢复所需数据并受数据库访问控制，不写普通日志。

恢复命令读取未完成操作，以 PostgreSQL 元数据和操作状态判断推进/补偿，执行幂等重试。正文使用有限内部操作标记以在重启后识别本次写入；不能只靠进程内 try/except 声称处理了崩溃恢复。v1 完成时记录恢复命令的精确位置、算法和现场演练。

同文档写入使用 PostgreSQL 文档级锁并带版本条件保护；持有锁到本次 SQL 提交/补偿完成。恢复过程也遵循锁顺序。创建时的锁以文档 ID 标识；不能要求文档行已经存在。幂等恢复不得增加第二次版本或复活软删除文档。

## 必须验证的行为

1. 原版五接口、所有字段、默认值、分页筛选、发布时刻、软删除和错误通过差分。
2. PATCH 的缺失/null、相同正文再次提交、空 PATCH、内容/摘要单独更新、Mongo version、UTF-16 长度/摘要以及中英混合字数有确定性测试。
3. Mongo 或 SQL 任一写失败、SQL 确定回滚、COMMIT 成功但回包异常、PG 持续不可用、补偿失败、进程步骤间中断都可检测并恢复；不误删成功正文、不遗留无说明的孤立正文。
4. 并发更新、重复删除/恢复不丢成功更新、不重复增加版本；原版对应外部结果保持兼容。
5. 生命周期正确关闭连接；测试不加载用户真实环境，不触碰旧数据卷；迁移 upgrade/downgrade 只对隔离库执行。
6. 所有质量门禁真实通过；README 提供实测安装、迁移、索引初始化、启动、契约和恢复步骤。

## 验收产物

代码、锁文件、迁移、合成数据、原版运行证据、差分报告、CI、README、`acceptance.md`、更新后的 status 和日志。版本进入 accepted 前，原版运行采集清单和关键失败恢复演练必须完成。

本规格中“如何完成可靠恢复”的内部选择由计划和测试落实，不授权修改既有 HTTP 错误契约、原业务表字段名或双库存储职责。

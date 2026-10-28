# 架构与目录规范

本文件适用于新 Python 项目。总体约束来自 [设计](design.md) 与 [已接受决策](decisions.md)。路线图展示最终模块，按版本创建需要的目录；禁止预先批量生成空模块。

## 总体结构

```text
knowledge-hub-fastapi/
├── AGENTS.md
├── README.md
├── pyproject.toml              # 包、依赖组、工具配置
├── uv.lock                     # 实施时生成并提交
├── src/knowledge_hub/
│   ├── main.py                 # ASGI 导出，不含业务逻辑
│   ├── app/
│   │   ├── factory.py          # create_app，装配依赖和错误处理
│   │   ├── lifespan.py         # 客户端连接与释放
│   │   └── routes.py           # 汇总各业务 APIRouter
│   ├── core/
│   │   ├── config.py           # 类型化配置与环境变量校验
│   │   ├── errors.py           # 稳定的应用错误类型
│   │   ├── logging.py          # 结构化日志和请求关联
│   │   ├── security.py         # 通用密码/JWT 原语，v7 起按需加入
│   │   └── ids.py              # ID 生成协议及实现
│   ├── integrations/
│   │   ├── postgres/          # engine、session、共享 ORM metadata
│   │   ├── mongodb/           # AsyncMongoClient 的生命周期
│   │   ├── redis/
│   │   ├── rabbitmq/
│   │   ├── elasticsearch/
│   │   ├── neo4j/
│   │   ├── object_storage/    # S3 兼容客户端，不在业务代码绑定 RustFS SDK
│   │   └── llm/               # 模型、Embedding、Reranker 的适配
│   ├── modules/
│   │   ├── documents/         # 元数据/正文/分类/版本
│   │   ├── ingestion/         # 文件、解析器及 Markdown 处理
│   │   ├── reviews/           # 审核与发布状态机
│   │   ├── identity/          # 登录、用户、角色、邮箱与密码流程
│   │   ├── access_control/    # 权限计算和文档可见性策略
│   │   ├── organizations/    # 团队树与成员
│   │   ├── search/           # 文档级全文搜索
│   │   ├── rag/              # 分块、混合召回、融合、重排
│   │   ├── knowledge_graph/  # 抽取、建图、图谱读取
│   │   ├── conversations/    # 会话、消息、问答、记忆和 Agent 调度
│   │   ├── engagement/       # 点赞、收藏、评论与分享
│   │   └── notifications/
│   └── workers/
│       └── document_pipeline/ # 消费入口、消息验证、调度，不承载业务算法
├── migrations/                # Alembic 元数据迁移与恢复表迁移
├── scripts/                   # 运维、回填、兼容快照和门禁命令
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── fixtures/             # 合成、脱敏、固定样本
├── deploy/                    # 容器与独立测试基础设施配置
└── docs/
    ├── refactor/
    ├── contracts/
    ├── versions/
    ├── templates/
    └── superpowers/plans/
```

## 模块内部职责

复杂模块按下面的依赖方向拆分，简单模块允许少层级，但不能把路由、SQL、外部调用和业务规则混在一个文件。

```text
api → application → domain
infrastructure → application 中的 ports / domain
app 装配具体 infrastructure，再注入 application 与 api
```

| 位置 | 可以做 | 不可以做 |
| --- | --- | --- |
| `api/` | 路由、请求校验、身份依赖、响应映射、协议适配 | SQL、Mongo 查询、提示词、业务状态转换 |
| `application/` | 一个明确用例的编排、事务、补偿、调用接口 | 导入 FastAPI Request/Response、直接绑定存储 SDK |
| `domain/` | 业务类型、不变量、纯规则、状态机 | 网络、数据库、全局设置或隐式 I/O |
| `infrastructure/` | 本模块仓储、SQL/Cypher/ES 查询、外部 API 适配 | 反向调用路由、替其他模块操作私有表 |
| `integrations/` | 共享连接、连接池、基础客户端配置 | 文档发布、审核等具体业务规则 |
| `workers/` | 消息接入、调度、重试与确认 | 复制一份 API 里的业务实现 |

v1 的 `documents` 同时访问双库并需要补偿，使用这四个职责目录。`application/commands/` 按创建、修改、删除分文件；`queries/` 按详情和分页分文件；请求、响应、映射和各仓储也分别存放。

跨模块只依赖公开应用接口、协议或事件，不导入别人的私有仓储。核心业务对象不含 ORM/Pydantic/SDK 类型。`core/` 不得逐渐变成承载所有业务的 `common`，不建立万能 `utils.py` 或全能 BaseService。

v1 Task 2 已将 `Clock/SystemClock` 放在 `core/clock.py`，轻量 `DocumentId` 放在 `core/identifiers.py`，避免 ID 基础设施反向依赖业务包。文档数据、命令、纯文本规则分别位于 `domain/document.py`、`commands.py`、`text_metrics.py`；应用层的异步 `DocumentStore` 只定义存储端口。不可变 `UpdateDocumentCommand.changes` 保留显式 null，`DocumentMutation.provided_fields` 必须沿用到写入器；不能按新旧内容相等与否推断版本动作。

`text_metrics` 保留原 JS 的空白集合和 UTF-16 单元语义，摘要截断可能得到未配对代理字符。Task 3 的 BSON 映射必须将这种字符按原 Node UTF-8 写入行为替换为 U+FFFD；Task 6 独立保证 JSON 转义兼容。不要把数据库编码清洗混入领域规则，也不能用 UTF-8 的 `errors="replace"` 生成问号来替代。

## 数据与客户端约束

- SQLAlchemy AsyncSession 按请求/任务独立创建；禁止多个并发协程共享一个 session。用例明确拥有提交/回滚边界。
- MongoDB 使用 PyMongo Async。正文的持久化字段保持原 camelCase；应用内部由映射转换。
- 外部BIGINT文本通过integrations/postgres/identifiers.bigint_parameter绑定为Text再CAST BIGINT，由数据库决定合法语法/范围和错误；不要用Python int或strip先处理。文档锁也先按PG规范化键，使16与0x10锁住同一行；内部Snowflake/DB读回ID是规范十进制数。此规则覆盖写入、查询和pending检查（D022）。
- 客户端由 lifespan 创建和关闭，不在模块 import 阶段连网，不每个请求新建连接池。
- v1 Task 3 的 PostgresDatabase 已分离业务engine与lock_engine：持有/等待session锁不占业务池；每池默认5+10连接、单进程两池最多30，部署必须按进程数预算。DocumentLock必须接lock_engine，不能因“复用连接”重新引入已复现的连接池饥饿；close需释放两池。
- PostgreSQL 迁移用 Alembic；Mongo 索引、ES mapping、Neo4j 约束、MQ 拓扑用有版本、可重复执行的初始化命令维护。
- 首轮保留所有存储职责。v1 只启动 PostgreSQL、MongoDB；其余随版本加入，不要求 v1 配齐模型、图谱和队列。
- 阻塞 SDK 封装在线程边界；CPU 密集解析进入受控 Worker；不能仅给同步函数加 `async` 就宣称非阻塞。

## 一致性方案

v1 使用跨库操作日志记录创建、修改、软删除的步骤、目标版本及补偿状态；记录与 PostgreSQL 元数据在同一 SQL 事务中维护可提交部分，显式处理 SQL 确定回滚后的 Mongo 补偿。操作日志包含恢复所需的有限快照并控制访问，不能把完整正文写入普通日志。

commit抛错不等于SQL确定回滚：提交可能成功而响应丢失。在线异常与重启恢复均须结束/丢弃旧连接，重取同文档session锁，再在新SQL事务取得对应日志行的FOR UPDATE锁。写入器从Mongo前持有此行锁到metadata/completed提交，因此恢复取得行锁才证明旧业务事务已结束；随后核对completed与元数据。已提交保留Mongo，确定未提交才补偿；SQL不可用或行锁仍被旧事务持有时保留pending并阻止同文档写，绝不凭查询暂未看到completed就补偿。

创建时先预分配Mongo ObjectId并在prepared快照仅保存content_id。补偿使用_id/documentId/operationId/version条件原子替换为空正文、deleted=true、creationFence=true的持久标记；不存在时upsert占住同一_id。迟到insert会因唯一_id失败，不能在SQL回滚/恢复后重建孤立正文。不得物理删除此标记或覆盖不同operation/version的正文；原API只读取未删除正文且无SQL元数据，标记不作为文档暴露。D021是内部可靠性扩展，代价为少量保留行；修改/删除补偿在Task5另证。

后续实现者需在 v1 故障测试中验证进程中断、Mongo 成功但 SQL 失败、补偿失败和重试。没有恢复证据的用例不能标记完成。

v3 在 PostgreSQL 增加事务 Outbox：业务状态和事件同事务提交，独立发布器发送；重复发布由消费者幂等处理。事件带任务 ID、文档 ID 和内容版本。索引任务读取最新文档状态，过期事件不能把已归档/删除内容重新暴露。

新可靠性表和内部状态字段属于添加式扩展，不改变原有业务表、正文集合和 HTTP 契约。现有数据导入、已有库 Alembic baseline 必须使用明确操作流程，不在启动时自动 stamp 或覆盖表。

Task3基础与Task4创建/查询及创建恢复已实现：prepare独立提交、pending门禁、单文档pending唯一、metadata/completed同事务、行锁屏障及条件补偿均有真实库证据。get对未决详情继续显式拒绝，恢复入口单独调用；mutate/soft_delete及其完整恢复仍待Task5，HTTP待Task6。不能把创建恢复测试当作全部写入或HTTP闭环验收。

## 问答与流式复用

非流式与流式入口调用共享的意图、检索、评估、改写、记忆和工具用例；输出适配器分别生成普通 JSON 与 AI SDK UI 消息流。提示词按用途独立成文件/常量模块，与 Cypher、SQL、事件编码分开。

身份、角色权限和数据可见性是不同检查。可见性策略生成 SQL、ES、Cypher 的等价过滤，结果与引用输出前再次检查；不在路由、检索器和图谱查询里分别发明不同规则。

## 配置及依赖锁定

实现默认选择 Python 3.12、uv、FastAPI/Pydantic、SQLAlchemy Async + asyncpg、Alembic、PyMongo Async；其余存储采用官方客户端或薄适配器。保留旧环境变量名称与单位，在配置层集中转换，禁止业务代码散读环境变量。

依赖必须锁定并通过安装及测试。库和框架建议依据官方文档：[FastAPI](https://fastapi.tiangolo.com/tutorial/bigger-applications/)、[SQLAlchemy](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html)、[PyMongo Async](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)、[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)。文档链接用于设计依据，实际版本以将来提交的 `uv.lock` 为准。

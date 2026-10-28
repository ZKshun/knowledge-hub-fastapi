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

## 数据与客户端约束

- SQLAlchemy AsyncSession 按请求/任务独立创建；禁止多个并发协程共享一个 session。用例明确拥有提交/回滚边界。
- MongoDB 使用 PyMongo Async。正文的持久化字段保持原 camelCase；应用内部由映射转换。
- 客户端由 lifespan 创建和关闭，不在模块 import 阶段连网，不每个请求新建连接池。
- PostgreSQL 迁移用 Alembic；Mongo 索引、ES mapping、Neo4j 约束、MQ 拓扑用有版本、可重复执行的初始化命令维护。
- 首轮保留所有存储职责。v1 只启动 PostgreSQL、MongoDB；其余随版本加入，不要求 v1 配齐模型、图谱和队列。
- 阻塞 SDK 封装在线程边界；CPU 密集解析进入受控 Worker；不能仅给同步函数加 `async` 就宣称非阻塞。

## 一致性方案

v1 使用跨库操作日志记录创建、修改、软删除的步骤、目标版本及补偿状态；记录与 PostgreSQL 元数据在同一 SQL 事务中维护可提交部分，显式处理 SQL 确定回滚后的 Mongo 补偿。操作日志包含恢复所需的有限快照并控制访问，不能把完整正文写入普通日志。

commit 抛错不等于 SQL 确定回滚：提交可能成功而响应丢失。在线异常处理和重启恢复均须结束/丢弃旧连接，重新取得同文档锁，确认旧事务已结束，再用新连接核验 completed 状态和元数据。已提交则保留 Mongo；确认未提交才补偿。数据库不可用或旧事务未确认结束时保留待恢复操作、拒绝后续同文档写入，绝不凭“查询暂未看到 completed”推断可以删除正文。

后续实现者需在 v1 故障测试中验证进程中断、Mongo 成功但 SQL 失败、补偿失败和重试。没有恢复证据的用例不能标记完成。

v3 在 PostgreSQL 增加事务 Outbox：业务状态和事件同事务提交，独立发布器发送；重复发布由消费者幂等处理。事件带任务 ID、文档 ID 和内容版本。索引任务读取最新文档状态，过期事件不能把已归档/删除内容重新暴露。

新可靠性表和内部状态字段属于添加式扩展，不改变原有业务表、正文集合和 HTTP 契约。现有数据导入、已有库 Alembic baseline 必须使用明确操作流程，不在启动时自动 stamp 或覆盖表。

## 问答与流式复用

非流式与流式入口调用共享的意图、检索、评估、改写、记忆和工具用例；输出适配器分别生成普通 JSON 与 AI SDK UI 消息流。提示词按用途独立成文件/常量模块，与 Cypher、SQL、事件编码分开。

身份、角色权限和数据可见性是不同检查。可见性策略生成 SQL、ES、Cypher 的等价过滤，结果与引用输出前再次检查；不在路由、检索器和图谱查询里分别发明不同规则。

## 配置及依赖锁定

实现默认选择 Python 3.12、uv、FastAPI/Pydantic、SQLAlchemy Async + asyncpg、Alembic、PyMongo Async；其余存储采用官方客户端或薄适配器。保留旧环境变量名称与单位，在配置层集中转换，禁止业务代码散读环境变量。

依赖必须锁定并通过安装及测试。库和框架建议依据官方文档：[FastAPI](https://fastapi.tiangolo.com/tutorial/bigger-applications/)、[SQLAlchemy](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html)、[PyMongo Async](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)、[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)。文档链接用于设计依据，实际版本以将来提交的 `uv.lock` 为准。

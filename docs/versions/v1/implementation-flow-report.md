# v1 文档服务学习讲义

这是一堂“用 FastAPI 完成第一个知识库后端模块”的课。学完本版，应能沿着一次文档请求，指出请求在哪里校验、业务规则在哪里执行、两种数据库分别保存什么，以及写到一半失败时如何收尾。v1 已完成的是**文档服务**；上传、解析、检索和 RAG 问答属于[后续版本](../../refactor/roadmap.md)。

本讲义讲实现思路和代码入口；逐例运行记录、命令与测试边界见[验收记录](acceptance.md)。本次只改讲义，没有重跑业务测试。

## 1. 本版学会了哪些需求闭环

| 学习主题 | 用户能完成的事 | 本版对应的技术要点 |
| --- | --- | --- |
| **HTTP 接口与契约** | 用原有 `/documents` 接口发请求，收到约定的状态码、字段和错误。 | FastAPI 路由、Pydantic 请求/响应模型、依赖注入、ASGI 中间件与异常处理。 |
| **文档完整生命周期** | 创建文档 → 列表和详情 → 修改 → 软删除 → 再查询得到 404。 | 每个动作一个应用用例；领域对象保存业务数据；路由只负责交接输入和输出。 |
| **双库存储** | 文档元数据和正文分别保存，详情能把它们重新组合。 | SQLAlchemy Async 操作 PostgreSQL，PyMongo Async 操作 MongoDB，以 `contentId` 关联。 |
| **跨库写入恢复** | 某一步失败后，系统能核对结果并恢复到可解释的状态。 | 持久操作日志、文档锁、条件写入、SQL 提交核对、补偿与可重试恢复命令。 |
| **可接续的工程** | 安装、初始化、启动、验证这套服务，并找到下一版的起点。 | `uv` 锁定依赖、Alembic、生命周期管理、测试与质量门禁、版本记录。 |

用一篇“FastAPI 学习笔记”贯穿本课：

1. 用 `POST /documents` 保存标题和正文。
2. 用 `GET` 查看列表和详情。
3. 用 `PATCH` 修改正文。
4. 用 `DELETE` 将文档隐藏，再查询确认它已不可见。

下面先给出代码地图，再逐步追踪这篇文档。

## 2. 文件树：到哪里读代码

把项目想成一条流水线：**外层接 HTTP，中间做业务，内层访问存储**。先看目录职责，再顺着第 3 节的图打开文件；不需要逐个读完 259 个文件。

```text
knowledge-hub-fastapi/
├── README.md / AGENTS.md                 运行入口、开发规则
├── pyproject.toml / uv.lock / .env.example 依赖、工具配置、环境变量样例
├── src/knowledge_hub/
│   ├── main.py                            Uvicorn 启动入口
│   ├── app/
│   │   ├── factory.py / lifespan.py       创建 FastAPI 应用；启动和关闭资源
│   │   ├── transport.py / body_reader.py  请求传输与有界解码
│   │   └── error_handlers.py / responses.py 错误与 JSON 输出
│   ├── core/                              配置、时钟、字符串 ID、日志
│   ├── integrations/postgres/             SQLAlchemy 连接与会话
│   ├── integrations/mongodb/              PyMongo Async 客户端
│   └── modules/documents/
│       ├── api/                           路由、Pydantic 模型、依赖与映射
│       ├── application/commands/          创建、修改、删除用例
│       ├── application/queries/           详情、分页用例
│       ├── application/ports.py           应用层要求的存储接口
│       ├── domain/                        文档数据与纯文本规则
│       └── infrastructure/                双库仓储、写入协调、日志与恢复
├── migrations/versions/0001_documents.py PostgreSQL 表结构
├── scripts/init_mongo_indexes.py         MongoDB 索引初始化
├── scripts/recover_document_operations.py 未决操作恢复命令
├── scripts/check_file_limits.py          Python 单文件行数门禁
├── deploy/compose.test.yml               隔离的测试双库
├── tests/{unit,integration,contract,e2e}/ 规则、真实库、接口契约、完整用户路径
├── tests/fixtures/                     固定请求/响应与数据库样本
├── .github/workflows/quality.yml         质量检查流程
└── docs/versions/v1/                     规格、各阶段报告、验收与本讲义
```

**本版新增/修改的范围**：

- 相对初始空 `main`（`5e43438`），v1 新增 **259** 个受版本控制文件，没有在该基准上修改既有文件。树里合并展示了重复的 `__init__.py` 与测试样本。
- v1 验收合并后，新增了本讲义，并修改 README、AGENTS、SOP、状态、决策、模板和验收等文档。
- 后续讲义调整只涉及文档；业务代码、迁移、测试及依赖锁没有随报告改动。

**建议的阅读顺序**：

1. 读 [router.py](../../../src/knowledge_hub/modules/documents/api/router.py)，找到五个 HTTP 入口。
2. 读 [create_document.py](../../../src/knowledge_hub/modules/documents/application/commands/create_document.py)，看创建用例如何处理业务规则。
3. 读 [document_store.py](../../../src/knowledge_hub/modules/documents/infrastructure/document_store.py)，看双库存储如何落地。

先建立请求主线，再研究恢复细节。

## 3. 跟着一次请求理解每项需求的实现链路

### 3.1 接口层：HTTP 请求如何进入 FastAPI

先看最小例子：客户端向 `POST /documents` 发送 `{"title":"FastAPI 学习笔记","content":"第一段正文"}`。请求经过 ASGI 中间件和路由；FastAPI 完成请求模型校验与依赖注入，业务动作由用例函数完成。

```mermaid
flowchart TD
    classDef default font-size:20px;
    A["发起：客户端 POST /documents"] --> B["Uvicorn / ASGI"]
    B --> C["app 中间件：解码、请求日志"]
    C --> D["APIRouter 选择创建入口"]
    D --> V["Pydantic 校验请求"]
    D --> E["Depends 取 DocumentServices"]
    V --> F["调用创建用例"]
    E --> F
    F --> G["响应模型：camelCase JSON，201"]
    V --> H["校验失败：约定的 400 错误"]
```

**这里的 FastAPI 知识点**：

- **应用装配**：[factory.py](../../../src/knowledge_hub/app/factory.py) 创建应用，挂载中间件、异常处理和路由。
- **路由**：[router.py](../../../src/knowledge_hub/modules/documents/api/router.py) 用装饰器声明路径与 HTTP 方法。
- **依赖注入**：[dependencies.py](../../../src/knowledge_hub/modules/documents/api/dependencies.py) 用 `Depends` 注入存储、时钟和 ID 生成器。
- **请求和响应模型**：[requests.py](../../../src/knowledge_hub/modules/documents/api/requests.py) 用 Pydantic 描述输入；[responses.py](../../../src/knowledge_hub/modules/documents/api/responses.py) 把内部 `snake_case` 映射为外部 `camelCase`。

**为什么还有协议适配层**：FastAPI 默认的校验错误、JSON 编码和请求体解析不一定等于项目已有接口。

- [transport.py](../../../src/knowledge_hub/app/transport.py) 和 [body_reader.py](../../../src/knowledge_hub/app/body_reader.py) 处理请求编码、表单和压缩等传输细节。
- [error_handlers.py](../../../src/knowledge_hub/app/error_handlers.py) 将异常转换为约定的错误格式。
- [重放测试](../../../tests/contract/test_v1_replay.py)使用固定的 [75 份接口与双库样本](../../../tests/fixtures/contracts/v1/manifest.json)，核对响应和数据副作用；另有 71 份传输样本，用于核对 HTTP 传输行为。

### 3.2 文档生命周期：创建、读取、修改、删除各做什么

应用层的一个函数对应一个动作。例如 `create_document()` 接受已经校验过的命令，产生 ID、默认草稿状态、字数和时间，然后调用 `DocumentStore`；它不认识 FastAPI 的 `Request`，也不自己写 SQL。`DocumentStore` 是应用层定义的接口，实际的 PostgreSQL + MongoDB 实现在基础设施层。

```mermaid
flowchart TD
    classDef default font-size:20px;
    A["发起：五个 /documents 操作"] --> B["api：请求映射与响应映射"]
    B --> C["application：一项动作一个用例"]
    C --> D["domain：文档状态、字数等规则"]
    C --> E["DocumentStore 接口"]
    E --> F["infrastructure：SQL / Mongo 仓储"]
    F --> G["结束：创建201、读取/修改/删除200；删除后404"]
```

五个操作的具体流转：

1. **创建** `POST /documents`：[create_document.py](../../../src/knowledge_hub/modules/documents/application/commands/create_document.py) 计算 ID、默认值和字数；存储层保存元数据与正文；接口返回包含字符串 ID、标题和正文的 201 响应。
2. **列表** `GET /documents`：[list_documents.py](../../../src/knowledge_hub/modules/documents/application/queries/list_documents.py) 交给 SQL 仓储筛选、排序和分页；接口返回 `items`、`total`、`page` 和 `pageSize`，不读取 Mongo 正文。
3. **详情** `GET /documents/{id}`：[get_document.py](../../../src/knowledge_hub/modules/documents/application/queries/get_document.py) 按 ID 找 SQL 元数据，再用 `contentId` 取 Mongo 正文并拼成详情；文档不存在时返回 404。
4. **修改** `PATCH /documents/{id}`：[update_document.py](../../../src/knowledge_hub/modules/documents/application/commands/update_document.py) 按明确提交的字段改值，并区分“未提交”和“提交 null”。显式提交 `content` 时，即使文本未变，正文版本也会加 1。
5. **软删除** `DELETE /documents/{id}`：[delete_document.py](../../../src/knowledge_hub/modules/documents/application/commands/delete_document.py) 触发双库删除标记并保留记录；之后列表不展示该文档，详情返回 404。

这里最值得练习的是**职责边界**：

- **路由**负责 HTTP 请求与响应。
- **应用用例**负责具体业务动作。
- **领域模型**：[document.py](../../../src/knowledge_hub/modules/documents/domain/document.py) 保存不依赖框架的文档数据。
- **存储实现**：[document_store.py](../../../src/knowledge_hub/modules/documents/infrastructure/document_store.py) 实现文档存取。

[连续 E2E 测试](../../../tests/e2e/test_document_lifecycle.py)把这些操作连起来，验证用户看到的结果和数据库实际状态一致。

**两个容易忽略的规则**：

- **文档 ID**：外部 ID 是十进制字符串，生成逻辑集中在 [ids.py](../../../src/knowledge_hub/core/ids.py)。
- **文本计算**：字数与正文摘要遵循原有 JavaScript 文本语义，纯计算放在 [text_metrics.py](../../../src/knowledge_hub/modules/documents/domain/text_metrics.py)。

因此路由无需知道雪花 ID 位布局，也无需在每个接口复制文本算法。

### 3.3 双库存储：一篇文档为什么要访问两个数据库

一篇文档的数据按职责分为两部分：

- **PostgreSQL**：保存标题、状态、作者和删除标记等元数据。
- **MongoDB**：保存正文及正文版本。
- **关联方式**：SQL 行中的 `contentId` 指向 Mongo 记录。列表只查 SQL；详情组合两库数据。

```mermaid
flowchart TD
    classDef default font-size:20px;
    A["发起：创建一篇文档"] --> B["DocumentStore"]
    B --> C["SQLAlchemy Async：写 PostgreSQL 元数据"]
    B --> D["PyMongo Async：写 MongoDB 正文"]
    C --> E["contentId 关联两条记录"]
    D --> E
    E --> F["详情：SQL 查元数据 + Mongo 查正文"]
    E --> G["列表：仅 SQL 筛选和分页"]
```

服务从准备到关闭的步骤：

1. 显式执行 [Alembic 迁移](../../../migrations/versions/0001_documents.py)，建立 SQL 表。
2. 显式运行 [Mongo 索引初始化脚本](../../../scripts/init_mongo_indexes.py)，建立唯一索引。
3. 启动服务时，[lifespan.py](../../../src/knowledge_hub/app/lifespan.py) 检查两库连接并装配 `PostgresMongoDocumentStore`。
4. 服务关闭时，生命周期管理器释放连接。这样无需在每个请求中重新建立连接。

应用启动只检查连通性，不自动改表或恢复；已有无版本业务库需要另行制定导入方案。

### 3.4 跨库一致性：写到一半失败时怎么办

PostgreSQL 和 MongoDB 各有自己的事务，不能假设写完 Mongo 就一定能提交 SQL。以修改正文为例：Mongo 已更新，而 SQL 提交回包丢失，此时客户端只知道“调用异常”，不知道 SQL 究竟成功还是失败。如果立刻把 Mongo 改回旧值，可能会撤销一笔其实已经成功的修改。

```mermaid
flowchart TD
    classDef default font-size:20px;
    A["发起：创建 / 修改 / 删除"] --> B["PG 先提交 prepared 操作日志"]
    B --> C["文档锁；业务事务锁住日志行"]
    C --> D["按版本和操作 ID 写 Mongo"]
    D --> E["PG 元数据 + completed 同事务提交"]
    E --> F["结束：返回用户结果"]
    D --> G["异常 / 进程中断"]
    E --> G
    G --> H["新事务取锁，确认旧事务结束"]
    H --> I["已提交：保留成功数据"]
    H --> J["确定未提交：条件补偿"]
    H --> K["暂不能确认：保留未决，稍后重试"]
```

**实现步骤与代码入口**：

1. **记录操作**：[operation_journal.py](../../../src/knowledge_hub/modules/documents/infrastructure/operation_journal.py) 先持久保存操作身份和恢复依据。
2. **保护并发**：[document_lock.py](../../../src/knowledge_hub/modules/documents/infrastructure/document_lock.py) 避免同一文档的并发写入互相干扰。
3. **组织写入**：[write_coordinator.py](../../../src/knowledge_hub/modules/documents/infrastructure/write_coordinator.py) 和 [mutation_writer.py](../../../src/knowledge_hub/modules/documents/infrastructure/mutation_writer.py) 协调双库写入。Mongo 条件写入比较版本和操作 ID，避免覆盖较新的数据。
4. **核对与恢复**：[recovery.py](../../../src/knowledge_hub/modules/documents/infrastructure/recovery.py) 判断应保留结果还是补偿；创建失败时留下内部空标记，阻止迟到的插入再次制造孤立正文。

**一次操作的可能结果**：

- **确认完成**：保留已经提交的数据。
- **确认未提交**：按条件补偿，恢复数据。
- **暂时无法确认**：保留未决状态，之后通过[恢复命令](../../../scripts/recover_document_operations.py)重试。

这一链路有真实双库、并发和故障测试，具体证据见[验收记录](acceptance.md)。

### 3.5 工程链路：服务怎样从代码变成可运行版本

```mermaid
flowchart TD
    classDef default font-size:20px;
    A["发起：锁定 Python 依赖"] --> B["显式迁移 SQL / 建 Mongo 索引"]
    B --> C["FastAPI lifespan 连通并装配服务"]
    C --> D["Uvicorn 提供五个接口"]
    D --> E["测试：规则 → 双库 → 契约 → E2E"]
    E --> F["结束：v1 验收并本地合并 main"]
```

学习时可以从这些入口追踪服务的运行过程：

1. [main.py](../../../src/knowledge_hub/main.py)：进程入口，启动 Uvicorn。
2. [factory.py](../../../src/knowledge_hub/app/factory.py)：装配 FastAPI 应用。
3. [lifespan.py](../../../src/knowledge_hub/app/lifespan.py)：管理数据库等资源的启动和关闭。
4. [README](../../../README.md)：提供锁定安装、初始化、启动和测试命令。
5. [质量工作流](../../../.github/workflows/quality.yml)：运行格式、lint、严格类型、300 行限制和测试检查。

v1 已在隔离双库上完整验证，并从 `v1` 分支合并到 `main`。2026-10-30，两个分支已推送至[公开 GitHub 仓库](https://github.com/ZKshun/knowledge-hub-fastapi)；云端 CI 的实际结果见[当前状态](../../refactor/status.md)。

## 4. 本课总结

读完本版后，可以沿一篇文档的创建、读取、修改和删除路径回答这三个问题：

1. 请求从哪里进入 FastAPI？
2. 业务规则和数据库操作分别位于哪一层？
3. 两库写入中断后，系统依据什么决定保留、补偿或重试？

**验收与后续范围**：

- 本版此前完整验收为 **451 项通过、0 跳过、覆盖率 94.71%**；合并后关键回归 **197 项通过**。数据来自[验收记录](acceptance.md)，本次整理讲义未重跑业务测试。
- v2–v21、旧业务库正式切换、整库停机或网络分区演练及生产发布仍未完成。代码托管状态和云端验证结果以[当前状态](../../refactor/status.md)为准。
- 下一版从[当前状态](../../refactor/status.md)继续。

# Knowledge Hub · FastAPI

企业级 RAG 知识库服务端的 Python + FastAPI 重构项目。按原项目 `v1`–`v21` 的功能边界递进实现，严格保留接口契约和 PostgreSQL、MongoDB、Elasticsearch、Neo4j、Redis、RabbitMQ、RustFS 的职责。

目标是让接手工程师和新会话中的 Coding Agent 都能清楚理解业务、定位代码、运行验证并继续上一阶段工作。

## 当前状态

当前处于 **v1 文档与实施准备阶段**：已建立规则、设计、版本路线、兼容策略和开发 SOP；Python 服务、依赖环境和自动化测试尚未实现。这里的业务闭环描述最终目标，不表示全部功能已经可用。

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
| 历次工作与证据 | [工作日志](docs/refactor/work-log.md) |

## 运行与验证

v1 计划采用 Python 3.12、uv、FastAPI、Pydantic、SQLAlchemy Async、Alembic 和 PyMongo Async。依赖的精确版本在实施时验证并写入锁文件。

当前没有服务启动命令可用。v1 完成后，这里必须补齐经过实际验证的安装、配置、数据库初始化、启动和测试命令；计划中的命令不是已经运行的证据。

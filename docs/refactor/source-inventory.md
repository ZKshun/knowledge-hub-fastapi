# 参考源与盘点边界

核实日期：2026-10-28。记录来自本地 Git 对象与工作区读取；未执行远端 fetch，不能代表之后的远端状态。

## 仓库与固定基线

| 参考 | 工作区相对位置/远端 | 固定提交 |
| --- | --- | --- |
| NestJS 后端 | `../knowledge-hub-backend`；https://gitcode.com/guang-agent/knowledge-hub-backend.git | 当前本地 main 与 origin/main 均为 `b4dc6b203a204079b89b978df66f62df74cc42b0`（v20） |
| 后端 v1 | 同上 origin/v1 | `f9dfce20ffe798dc35ede0a74219f06bf3d6980f` |
| 后端 v21 | 同上 origin/v21 | `3dac13836d358390a42f54b8959aec3ebe279177` |
| 前端后期参考 | `../knowledge-hub-frontend`；https://gitcode.com/guang-agent/knowledge-hub-frontend.git | origin/v18 `c9f7bd84dfac993a0478fc60f77a12520a64e8dd` |

本地后端 main 已由用户 pull，已核对为最新本地远端跟踪基线。旧结论“本地 main 停在 v6”已失效。v21 仍需作为独立参考分支读取。

v1–v5 分支历史存在分叉，迁移以每个固定版本的最终文件树和对比结果为准，不仅依靠 `git log previous..next`。每版启动时记录 `git rev-parse origin/vN`，后续不悄悄漂移基线。

## 核心证据位置（均为旧仓库相对路径）

| 内容 | 位置 |
| --- | --- |
| 路由和 DTO | `src/*/*.controller.ts`、`src/*/dto/` |
| v1 文档 CRUD | `src/document/document.service.ts`、`entities/document.entity.ts`、`schemas/document-content.schema.ts` |
| 数据结构与种子 | `init-scripts/postgresql/init.sql`、`init-scripts/mongodb/init.js` |
| 服务装配与环境 | `src/main.ts`、`src/app.module.ts`、`.env.example`、`docker-compose.yml` |
| 消息与管线 | `src/mq/`、`src/pipeline/` |
| 权限可见性 | `src/auth/`、`src/document/document-access.ts`、`src/team/` |
| 对话与评测 | `src/ai/`、`src/ai/eval/`、`src/observability/` |
| 人工样例 | `curl*.md`、`chat-memory.md`、`agentic-rag.md`、`test-files/` |
| 前端调用协议 | 前端 `src/api/client.ts`、`src/api/index.ts`、`src/types.ts`、`src/pages/ChatPage.tsx` |

用 `git show <固定 SHA>:<路径>` 读取参考，无需切换现有工作区。禁止直接改动旧仓库以便迁就新实现。需要运行旧版本时使用独立 checkout/worktree 和隔离测试配置，先检查已有工作区。

## 已确认技术事实

- PostgreSQL 存业务元数据；MongoDB `document_content` 存正文，`content_id` 对应 ObjectId，`documentId` 对应字符串雪花 ID。
- Elasticsearch `kh_document` 为文档搜索索引，`kh_chunk` 为分块与 dense_vector 索引；Neo4j 为抽取的实体关系。
- Redis 用于验证码及会话热窗口；RabbitMQ 消费器触发全文、向量和图谱处理；RustFS 使用 S3 兼容接口。
- 前端默认访问 `/api`，Vite 代理移除该前缀。后端自身没有统一 `/api` 前缀。
- 前端 v18 使用 `@ai-sdk/react`、`DefaultChatTransport` 消费 `/ai/chat/stream`，不能只迁移为任意 SSE 文本流。
- v21 包含分类、互动、分享、版本、通知，但当前已知前端分支没有 v21 的相应完整页面。
- 已检查的后端测试主要为默认 `/` 返回 Hello World；不能将现有测试作为业务完整性证明。

## 风险与范围

大文件、跨库补偿不完整、消息失败恢复、索引权限同步等需要在新项目设计和验证。这里不是对旧系统的完整审计，不能从抽样静态读取推导“所有接口均已运行正确”。

当前只读了 `.env.example`；实际密钥不得写入契约、日志或提交。旧 `test-files/` 可能包含个人资料，测试应优先生成匿名合成数据，不能直接把样本复制到新仓库。

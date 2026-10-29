# Coding Agent 项目入口

## 必须遵守

1. 将 NestJS 企业 RAG 服务端迁移至 Python + FastAPI，严格兼容对应版本的 HTTP、JSON、流式协议和多数据库架构。
2. 按 `v1`、`v2`、…、`vN` 开发；每个版本分支都从最新已验收的 `main` 派生；本版验收后合并回 `main`，下一版再从更新后的 `main` 派生。禁止从未合并的 `vN` 直接创建 `vN+1`。
3. `main` 只接收验收通过的版本；业务开发在版本分支完成。用户已要求逐版验收后本地合并 main，无需为这一既定流程反复确认；推送、发布另按授权执行。不得把验收通过等同于已经合并或推送。
4. 新 Python 生产代码每文件不超过 **300 物理行（含空行和注释）**，目标不超过 200 行；按职责拆分。此限制不用于清理旧 NestJS 文件。
5. 外部 ID 保持字符串，JSON 保持 `camelCase`，内部 Python 使用 `snake_case`；不得擅自改接口、合并存储或提前加入后续版本功能。
6. 开工、阶段切换、结束前都更新任务状态；未经执行的测试写“未运行”，不得声明版本完成。
7. 每版逐项汇报需求、实现、验证和未完成事项；验收记录保存对照，并提供需求→入口/模块→存储或副作用→失败恢复→响应→证据的链路报告，不能只列文件或测试数量。

## 每次新会话先读

按顺序读取 [README](README.md)、[当前状态](docs/refactor/status.md)、[开发 SOP](docs/refactor/agent-sop.md)、状态文件指定的当前版本规格和计划；再检查 Git 分支、提交和未提交变更。它们是恢复上下文的必要材料。

## 按任务渐进读取

| 任务 | 必须读取 |
| --- | --- |
| 理解总体任务和既定决策 | [设计](docs/refactor/design.md)、[决策记录](docs/refactor/decisions.md) |
| 选择版本、确认本版边界 | [版本路线](docs/refactor/roadmap.md)、[源系统盘点](docs/refactor/source-inventory.md) |
| 写代码、规划目录和依赖 | [架构](docs/refactor/architecture.md)、[代码规范](docs/refactor/code-standards.md) |
| HTTP、DTO、数据库、MQ、流式、权限 | [兼容策略](docs/refactor/compatibility.md)、[对应版本契约](docs/contracts/README.md) |
| 实现 v1 | [v1 规格](docs/versions/v1/spec.md)、[v1 实施计划](docs/superpowers/plans/2026-10-28-v1.md) |
| 验收、合并、跨会话交接 | [开发 SOP](docs/refactor/agent-sop.md)、[验收与交接模板](docs/templates/version-record.md)、[工作日志](docs/refactor/work-log.md) |

规范发生冲突时，以用户最新明确指令为先，随后是本文件、已接受决策、专题规范、版本规格和实施计划。发现矛盾先记录并纠正依赖文档，不自行降低已确认约束。会改变功能、契约或存储架构的事项需由用户决定；普通实现细节可自行处理并留记录。

v1 已验收并本地合并 main；v2 尚未创建。实际状态以 `docs/refactor/status.md` 加 Git 检查为准，不从路线图或目录存在推断完成度。

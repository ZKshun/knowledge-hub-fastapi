# 当前重构状态

最后更新：2026-10-28。此文件是新会话入口中的当前状态摘要；先与实际 Git 核对。

## 当前定位

- 项目：`knowledge-hub/knowledge-hub-fastapi`，独立 Git 仓库。
- 当前版本：**v1**；阶段：**planned（规则与实施准备已完成，业务实现未开始）**。
- 当前分支：`v1`，直接从本地 main 创建。
- 起点 main SHA：`5e43438`（空的仓库初始化提交）。当前 HEAD 使用 `git rev-parse HEAD` 查询；不在同一提交中自引用提交 SHA。
- 当前无 remote；尚未合并、推送、发布或打标签。
- 来源后端 v1：`f9dfce20ffe798dc35ede0a74219f06bf3d6980f`。
- 参考后端本地 main：`b4dc6b2`，与本地 origin/main 一致，已取代旧的 v6 结论。

## 已完成

- [x] 用户确认接口/多数据库严格兼容、架构、代码规范、版本映射和跨会话文档方式。
- [x] 按用户修正规则记录 main→vN→验收→main，创建 Python main 和 v1。
- [x] 建立 README 业务闭环、精简 AGENTS、架构/兼容/质量/SOP/决策与路线文档。
- [x] 提取 v1 源码契约，写出 v1 规格和可执行实施计划。

## 尚未完成

- [ ] 原 NestJS v1 隔离运行、契约夹具及运行差分证据。
- [ ] Python pyproject、uv.lock、依赖安装和服务骨架。
- [ ] PostgreSQL/MongoDB 仓储、迁移、CRUD、补偿/恢复工具。
- [ ] CI 门禁、单元/集成/契约/E2E、覆盖率和实测 README。
- [ ] v1 验收、合并 main；v2–v21 全部未开始。

## 下一项可直接执行的任务

按 [v1 实施计划](../superpowers/plans/2026-10-28-v1.md) **Task 1：原版契约基线与差分工具** 开始。先检查 Python 仓库干净程度、读取 [v1 规格](../versions/v1/spec.md) 和 [契约](../contracts/v1.md)，再为原版固定 SHA 准备隔离运行环境和匿名数据。

不要先启动 v2、改旧后端、切换有用户更改的参考工作区、或把默认 FastAPI 错误格式作为完成实现。

## 验证与运行资源

本轮只做文档治理。实际文档验证结果与审查反馈记在 [工作日志](work-log.md)；未运行 Python 服务或业务测试，不能将文档校验等同于代码测试通过。

没有由本轮启动的应用进程或容器。未使用旧数据库数据卷。依赖、Docker/测试端口的可用性尚需在 Task 1 实测；当前没有已知必须由用户解除的业务阻塞。

## 必须读取

1. [开发 SOP](agent-sop.md)
2. [v1 规格](../versions/v1/spec.md)
3. [v1 计划](../superpowers/plans/2026-10-28-v1.md)
4. [v1 契约](../contracts/v1.md)
5. 按工作需要读取 [架构](architecture.md)、[代码规范](code-standards.md)、[兼容策略](compatibility.md)

接续时同步更新本文件、计划勾选和工作日志。只有完成实际验收且合并 main 后，才把当前版本切换至 v2。

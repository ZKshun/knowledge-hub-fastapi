# 当前重构状态

最后更新：2026-10-28。此文件是新会话入口中的当前状态摘要；先与实际 Git 核对。

## 当前定位

- 项目：`knowledge-hub/knowledge-hub-fastapi`，独立 Git 仓库。
- 当前版本：**v1**；阶段：**implementing（Task 1 已完成，下一项 Task 2 尚未开始；业务接口未实现）**。
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
- [x] Task 1：原版固定源码隔离构建/运行、75 份 HTTP/双库证据、严格比较器、并列时间断言及独立审查修复。
- [x] Python 3.12 独立环境、pyproject/uv.lock 和基础工具配置；31 项现有测试通过，Ruff/mypy 通过。
- [x] 新增 D015：每版必须向用户逐项汇报需求、实现方式、验证及未完成事项，并保存同一对照表。

## 尚未完成

- [ ] Task 2：领域类型/纯规则、配置、Clock/雪花 ID 和文件行数门禁。
- [ ] FastAPI 服务骨架及真实接口；新旧服务差分尚未执行。
- [ ] PostgreSQL/MongoDB 仓储、迁移、CRUD、补偿/恢复工具。
- [ ] CI 门禁、单元/集成/契约/E2E、覆盖率和实测 README。
- [ ] v1 验收、合并 main；v2–v21 全部未开始。

## 下一项可直接执行的任务

按 [v1 实施计划](../superpowers/plans/2026-10-28-v1.md) **Task 2：领域规则、配置、ID 与规模门禁** 开始。先检查 Git/现有变更，读取 [v1 规格](../versions/v1/spec.md)、[已验证契约](../contracts/v1.md) 和 [Task 1 需求与实现报告](../versions/v1/task-1-report.md)。Task 1 不要重复实现或重新覆盖证据；只有确需补充基线时才按复现文档在新目录采集。

不要先启动 v2、改旧后端、切换有用户更改的参考工作区、或把默认 FastAPI 错误格式作为完成实现。

## 验证与运行资源

Task 1：31 passed、0 skipped、0 failed；包括真实 MongoDB 索引准备和全部证据哈希/归一化验证。Ruff、mypy strict（13 个源文件）通过，最长手写生产/脚本文件 105 行。完整 v1 的生产覆盖率、CRUD、故障恢复及新旧服务差分尚未验证，不能据此验收 v1。

本轮旧服务 PID 12852 和 `kh-fastapi-v1-test` 的 PostgreSQL/MongoDB 容器已停止，测试卷保留；3101/55432/57017 已释放。未使用旧数据卷。`.local/legacy-v1` 保留源副本，`.local` 内保留原始采集备份和测试临时目录，均被忽略。当前无需要用户解除的阻塞。

当前主机系统 pytest 临时目录有账户权限差异；需要 tmp_path 的测试应使用新命名的项目内 `--basetemp=.local/pytest-runs/<本次标识>`，父目录先建立。需要真实库测试时按 [基线复现](../versions/v1/contract-baseline.md) 启动两个专用容器并设置环境开关。下一 Task 2 的纯单元逻辑不需要启动旧 HTTP 服务。

## 必须读取

1. [开发 SOP](agent-sop.md)
2. [v1 规格](../versions/v1/spec.md)
3. [v1 计划](../superpowers/plans/2026-10-28-v1.md)
4. [v1 契约](../contracts/v1.md)
5. 按工作需要读取 [架构](architecture.md)、[代码规范](code-standards.md)、[兼容策略](compatibility.md)

接续时同步更新本文件、计划勾选和工作日志。只有完成实际验收且合并 main 后，才把当前版本切换至 v2。

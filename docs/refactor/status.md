# 当前重构状态

最后更新：2026-10-29。此文件是新会话入口中的当前状态摘要；先与实际 Git 核对。

## 当前定位

- 项目：`knowledge-hub/knowledge-hub-fastapi`，独立 Git 仓库。
- 当前版本：**v1**；阶段：**implementing（Task1–5已完成，下一项Task6；HTTP接口未实现）**。
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
- [x] Task 2：领域与存储协议、JS 文本规则、显式配置、Clock/雪花 ID、300 行门禁；实现/验证/独立审查通过。
- [x] Task 3：兼容迁移、双库读取/BSON映射、独立连接池文档锁和持久操作日志；完整133项测试无跳过，独立审查无待修复项。
- [x] Task4：创建与查询用例、可恢复创建、事务行锁屏障及空正文防迟到标记；审查1项BIGINT问题已修复，完整172项无跳过。
- [x] Task5：修改/软删除用例、完整恢复、内部CAS屏障、并发保护及独立恢复CLI；NUL快照问题经RED→GREEN修复，完整242项无跳过。

## 尚未完成

- [ ] Task6：FastAPI服务骨架、五接口、协议/错误/生命周期适配及完整新旧差分。
- [ ] CI 门禁、单元/集成/契约/E2E、覆盖率和实测 README。
- [ ] v1 验收、合并 main；v2–v21 全部未开始。

## 下一项可直接执行的任务

按[v1计划](../superpowers/plans/2026-10-28-v1.md) **Task6：FastAPI五接口与兼容适配**开始。先核对Git，读取[v1规格](../versions/v1/spec.md)、[契约](../contracts/v1.md)、[Task5报告](../versions/v1/task-5-report.md)及D020–D024。当前store已完整实现DocumentStore，五个应用用例可复用；从真实五接口失败测试开始，保留camelCase/字符串ID/POST201/分页/原400和500语义，不能返回默认422。lifespan显式装配/关闭双池PG和Mongo。

使用75份固定原版证据完成HTTP/双库差分，不覆盖expected。Mongo差分只能单独断言并排除合法operationId/rollback标记及空creationFence，不能忽略全部deleted业务记录。PATCH显式content即使相同也增版本；PATCH空正文允许，create空正文为原500；PATCH非空字段null的InvalidDocumentChange也须映射原500。外部BIGINT仍交PG原生CAST。不要重复Task1–5或提前启动v2。

不要先启动 v2、改旧后端、切换有用户更改的参考工作区、或把默认 FastAPI 错误格式作为完成实现。

## 验证与运行资源

Task 1：31 passed、0 skipped、0 failed；包括真实 MongoDB 索引准备和全部证据哈希/归一化验证。Ruff、mypy strict（13 个源文件）通过，最长手写生产/脚本文件 105 行。完整 v1 的生产覆盖率、CRUD、故障恢复及新旧服务差分尚未验证，不能据此验收 v1。

Task 2 本轮：完整测试113 passed、1 skipped（旧库探针未启用）；当前 src 覆盖率96.68%。Ruff/check、mypy strict（src/scripts 27文件）与文件门禁通过，最长105/300行。该覆盖率不包含尚未实现的 CRUD、恢复与 HTTP，不能验收 v1。

Task 3 当前：KH_RUN_STORAGE_DB_TESTS=1、KH_RUN_LEGACY_DB_TESTS=1，完整133 passed、0 skipped；当前生产覆盖95.10%。Ruff format/check、mypy strict（src/scripts/migrations 46文件）与行数门禁（44生产/脚本文件，最长105行）通过；uv lock --check --offline通过。尚未实现的写入恢复与HTTP/E2E不计作通过。

Task4最终：两个DB开关均1，完整172 passed、0 skipped，生产覆盖95.12%；Ruff format/check、mypy strict56文件、行数54文件最长133行通过。新增17项双库故障/恢复、10项用例单元、12项BIGINT原生解析/锁回归。独立审查1项Important经RED→GREEN修复、完整回归通过，无Critical/Minor，未二次审查。OS kill/整个PG容器关闭未执行，模拟中断及业务连接拒绝边界见Task4报告。

Task5最终：两个DB开关均1，task5-final-015完整242 passed、0 skipped、0 failed，生产覆盖95.01%；Ruff format123文件/check、mypy strict67文件、行数64文件最长133/300、uv lock45依赖通过。新增16项用例单元+54项真实库/子进程/恢复/并发测试；独立审查确认同一自查NUL快照Important，4项RED→编码修复→40项受影响GREEN，再完整242回归。无其他Critical/Important/Minor，未二次审查。具体测试边界及需求对照见[Task5报告](../versions/v1/task-5-report.md)。

Task1旧服务PID12852保持停止，本阶段没有启动HTTP。Task5验证后两个`kh-fastapi-v1-test`容器已停止并核对Exited(0)，卷保留，临时SQL schema/Mongo集合0残留。未使用旧数据卷。`.local/legacy-v1`保留源副本，`.local`内保留原始采集备份、实际测试输出和临时目录，均被忽略。当前无需要用户解除的阻塞。

当前主机系统pytest临时目录有账户权限差异；需要tmp_path时使用新命名的项目内`--basetemp=.local/pytest-runs/<本次标识>`，父目录先建立。真实库测试按[Task3复现](../versions/v1/task-3-report.md)启动两个专用容器并设两个环境开关。Task6需真实双库，原HTTP仅在确需新旧对比时启动，不重复采集覆盖历史快照。

## 必须读取

1. [开发 SOP](agent-sop.md)
2. [v1 规格](../versions/v1/spec.md)
3. [v1 计划](../superpowers/plans/2026-10-28-v1.md)
4. [v1 契约](../contracts/v1.md)
5. 按工作需要读取 [架构](architecture.md)、[代码规范](code-standards.md)、[兼容策略](compatibility.md)

接续时同步更新本文件、计划勾选和工作日志。只有完成实际验收且合并 main 后，才把当前版本切换至 v2。

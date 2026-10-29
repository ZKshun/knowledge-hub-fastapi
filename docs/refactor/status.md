# 当前重构状态

最后更新：2026-10-29。此文件是新会话入口中的当前状态摘要；先与实际 Git 核对。

## 当前定位

- 项目：`knowledge-hub/knowledge-hub-fastapi`，独立 Git 仓库。
- 最新交付：**v1 merged**；下一版本：**v2 planned，分支尚未创建**。
- 当前分支：`main`；v1从原main `5e43438819bb660612799983c6af52bdef99941e`派生，验收提交`75f62ed639f784cac5c2e039ac9afcb622327aa5`，本地合并提交`d1d4a2703d6be62a4ce11efad9627fe874e897a6`。本文件后续文档提交可能使main HEAD前进，始终先以Git核对。
- 当前无 remote；v1已本地合并，未推送、发布或打标签；云端CI未运行。
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
- [x] Task6：五个FastAPI文档接口、原请求/错误/传输、双库生命周期、日志与入口；原75项双库差分、65项传输及SQL文本编码补证通过。独立审查3项Important经同轮修复，最终444项无跳过、覆盖94.85%，见[需求与实现报告](../versions/v1/task-6-report.md)。
- [x] Task7：版本化原版SQL测试夹具、只读固定Action质量工作流、锁定依赖干净安装、全新隔离双库和正式CLI真实TCP实测；全分支审查发现的表单根级键与数字错误顺序已由真实旧服务证据RED→GREEN修复，最终451项0跳过、覆盖94.71%，静态门禁及文档审计通过；见[验收记录](../versions/v1/acceptance.md)和[一页报告](../versions/v1/implementation-flow-report.md)。云端CI因无remote未运行。
- [x] v1验收后以`--no-ff`本地合并main，合并树与v1验收树相同；合并后原版契约/E2E关键回归197项通过、0跳过。v1分支保留。

## 尚未完成

- [ ] v2–v21全部未开始；v2尚无分支、规格、契约或实现。当前无remote，云端CI仍待将来托管平台运行。

## 下一项可直接执行的任务

下次按用户要求开始v2时：先核对main实际HEAD/工作区及[验收记录](../versions/v1/acceptance.md)，读取[开发SOP](agent-sop.md)、[版本路线](roadmap.md)及旧NestJS v2来源；从**更新后的main**新建`v2`，先做v2源功能/协议/多数据库变化盘点，编写`docs/versions/v2/spec.md`、`docs/contracts/v2.md`和分步计划，再按契约→实现→验证→验收循环推进。v2范围为上传、PDF/DOCX/PPTX/XLSX/TXT解析与RustFS；具体接口以固定v2源码与运行证据为准，不沿用聊天猜测。v1不需重做，不推送/发布。

## 验证与运行资源

Task 1：31 passed、0 skipped、0 failed；包括真实 MongoDB 索引准备和全部证据哈希/归一化验证。Ruff、mypy strict（13 个源文件）通过，最长手写生产/脚本文件 105 行。完整 v1 的生产覆盖率、CRUD、故障恢复及新旧服务差分尚未验证，不能据此验收 v1。

Task 2 本轮：完整测试113 passed、1 skipped（旧库探针未启用）；当前 src 覆盖率96.68%。Ruff/check、mypy strict（src/scripts 27文件）与文件门禁通过，最长105/300行。该覆盖率不包含尚未实现的 CRUD、恢复与 HTTP，不能验收 v1。

Task 3 当前：KH_RUN_STORAGE_DB_TESTS=1、KH_RUN_LEGACY_DB_TESTS=1，完整133 passed、0 skipped；当前生产覆盖95.10%。Ruff format/check、mypy strict（src/scripts/migrations 46文件）与行数门禁（44生产/脚本文件，最长105行）通过；uv lock --check --offline通过。尚未实现的写入恢复与HTTP/E2E不计作通过。

Task4最终：两个DB开关均1，完整172 passed、0 skipped，生产覆盖95.12%；Ruff format/check、mypy strict56文件、行数54文件最长133行通过。新增17项双库故障/恢复、10项用例单元、12项BIGINT原生解析/锁回归。独立审查1项Important经RED→GREEN修复、完整回归通过，无Critical/Minor，未二次审查。OS kill/整个PG容器关闭未执行，模拟中断及业务连接拒绝边界见Task4报告。

Task5最终：两个DB开关均1，task5-final-015完整242 passed、0 skipped、0 failed，生产覆盖95.01%；Ruff format123文件/check、mypy strict67文件、行数64文件最长133/300、uv lock45依赖通过。新增16项用例单元+54项真实库/子进程/恢复/并发测试；独立审查确认同一自查NUL快照Important，4项RED→编码修复→40项受影响GREEN，再完整242回归。无其他Critical/Important/Minor，未二次审查。具体测试边界及需求对照见[Task5报告](../versions/v1/task-5-report.md)。

Task6最终：两个DB开关均1，task6-final-026完整444 passed、0 skipped、0 failed，生产语句+分支覆盖94.85%，约197秒。Ruff check/format最终170文件通过；mypy strict94文件、行数91生产/脚本文件最长137/300、uv锁46依赖通过。独立审查0Critical/3Important/0Minor；Uvicorn异常泄漏、解码/压缩和JSON词法经一次修复轮RED→GREEN，未二次审查。补SQL文本编码与显式dotenv回归，细节见Task6报告。

Task7及合并最终：新锁定环境46依赖；新双库完整451 passed、0 skipped、94.71%，约181秒；Ruff format171文件/check、mypy strict94文件、生产/脚本91文件最长137/300、uv锁检查通过。正式CLI真实TCP五接口及SQL/Mongo状态通过；合并树与v1树相同，合并后契约/E2E197项通过。Task7审查0Critical/1Important/1Minor，后两项均按精确兼容要求经原版真实HTTP RED→GREEN修复，未二次独立审查。详细边界见[验收记录](../versions/v1/acceptance.md)。

Task1旧服务保持停止；Task7补采的原版HTTP进程在finally停止，正式FastAPI进程关闭；3101/38121无监听。最终只读审计临时SQL schema/Mongo集合均0残留；`kh-fastapi-v1-test`与本轮`kh-fastapi-v1-acceptance`各两个容器stop后均Exited(0)，卷保留。未使用旧数据卷，参考前后端Git均干净。`.local/legacy-v1`保留源副本，`.local`内保留原始采集和实际输出，均被忽略。当前无需要用户解除的阻塞。

当前主机系统pytest临时目录有账户权限差异；需要tmp_path时使用新命名的项目内`--basetemp=.local/pytest-runs/<本次标识>`，父目录先建立。真实库测试按[Task3复现](../versions/v1/task-3-report.md)启动两个专用容器并设两个环境开关。原HTTP仅在确需新旧对比时启动，不重复采集覆盖历史快照。

## 必须读取

1. [开发 SOP](agent-sop.md)
2. [版本路线](roadmap.md)与[v1验收记录](../versions/v1/acceptance.md)
3. 准备v2时先核对旧NestJS v2源，创建并读取v2规格、契约和计划；沿用的v1边界见[v1契约](../contracts/v1.md)
4. 按工作需要读取 [架构](architecture.md)、[代码规范](code-standards.md)、[兼容策略](compatibility.md)

接续时同步更新本文件、计划勾选和工作日志。v1已合并main；v2须从更新后的main创建，不能从v1派生。

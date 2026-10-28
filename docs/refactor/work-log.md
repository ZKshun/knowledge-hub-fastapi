# 重构工作日志

历史只追加；当前状态以 [status.md](status.md) 为准。命令未执行时明确写未运行，不能复用旧输出冒充本轮验证。

## 2026-10-28 · 文档与规则基线

- 用户接受：FastAPI 模块化单体/Worker、原版本映射、严格接口与多库兼容、Python 文件约束；要求规则渐进披露并支持多个会话接续。
- 分支规则更正：每个 vN 必须从最新 main 创建，验收后合并 main。此前“vN 直接派生 vN+1”不再适用。
- 只读核验：后端本地 main 和 origin/main 均为 b4dc6b2（v20）；origin/v21 为 3dac138；v1 固定 f9dfce2。前端流式使用 AI SDK，代理移除 /api 前缀。
- 新建独立 Python 仓库，空 main 起点 5e43438，从 main 派生 v1。本地 Git 写入遇到沙箱账户权限及 ownership 差异，通过正式审批和仅本次命令的精确 safe.directory 完成；未修改全局 Git 信任配置。
- 写入 README、AGENTS、总体设计、源盘点、决策、路线、架构、规范、兼容策略、开发/恢复/验收 SOP、v1 规格与计划、契约入口、状态和模板。
- Python 业务代码、依赖、服务、数据库、模型调用和业务测试：均未开始。
- 独立文档审查发现并已修正两项 P1：PATCH 显式字段信息丢失会误判正文版本；COMMIT 回包异常不能直接补偿 Mongo。已同步规格、契约、架构、接口签名和故障测试计划；独立复核确认两项闭合。此审查不代表代码运行验证。
- 本地 Markdown 检查：PowerShell 枚举 18 个 Markdown（含工作区导航），逐项解析相对链接，67 个本地链接、0 失效；代码围栏均配对；路线完整覆盖 v1–v21；Python 根 AGENTS 为 29 物理行。
- Git 检查：`git merge-base main v1` 为 5e43438819bb660612799983c6af52bdef99941e，确认 v1 直接派生 main；`git remote -v` 无输出；旧后端与前端 `git status --porcelain` 均无输出。
- 文档差异以暂存后 `git diff --cached --check` 验证；本轮提交信息为 `docs: establish FastAPI migration governance and v1 plan`。实际提交 SHA 用 `git log -1 --oneline` 核对，避免同一提交中自引用。
- 已增加 `.gitattributes` 固定文本 LF；只提交新 Python 仓库文档和 Git 规则，工作区导航 AGENTS 不属于 Git 仓库。下一会话克隆 Python 仓库仍可从其根 AGENTS 独立接续。

## 2026-10-28 · v1 Task 1：契约基线与差分工具

- 本轮开始前 HEAD：fb05656，分支 v1，工作区干净；本轮只执行用户要求的下一步 Task 1。
- 用户新增 D015：每版逐项汇报做了哪些需求、分别如何实现、验证和未完成事项；已同步 AGENTS、SOP、模板与计划全局约束，并形成 [本阶段需求与实现对照](../versions/v1/task-1-report.md)。
- 建立 Python 3.12.14/uv 独立环境、pyproject、uv.lock；同步 API 所需依赖在此阶段只锁定，不代表服务已实现。
- 从固定 f9dfce2 导出 `.local/legacy-v1`。首次导出遭遇 Git Windows CRLF 转换，字节校验拒绝；使用单次 core.autocrlf=false 重新导出并构建。Nest deleteOutDir=true；本次构建/启动 PID、路径、工作目录、环境与端口证据保存在阶段报告。
- 启动专用 PostgreSQL16.15/Mongo7.0.43 容器，仅用 knowledge_hub_fastapi_test；旧 API 使用 3101，未切换或修改原参考工作区。
- 最终采集75份真实HTTP与双库快照，manifest记录来源/构建/依赖/夹具哈希；原始和归一化证据并存，包含创建/更新/删除/补偿失败、Unicode和并列时间场景。早先采集分别保存在.local备份，未删除证据。
- TDD记录：比较器/采集器缺失先失败；连接参数覆盖、动态ID错误消息、日期Z/offset和同时间排序分别观察到失败再实现。真实Mongo索引初始化冲突先在集成测试复现，再兼容原初始化脚本的唯一索引。
- 独立代码审查：1项Important（同创建时间排序缺少运行证据），无Critical/Minor；已在一次修复中补真实GET及组内无序/组间有序断言，完整回归通过。未声称审查者又执行了修复后的回归；修复验证由实现者完成。
- 实际验证：Ruff format/check通过；mypy strict检查13个源文件通过；KH_RUN_LEGACY_DB_TESTS=1，`uv run --locked --link-mode=copy pytest -q --basetemp=.local/pytest-runs/task1-final-007` → **31 passed，0 skipped，0 failed**；最长手写生产/脚本Python文件105行。未运行完整FastAPI服务覆盖率或新旧服务差分。
- 运行环境处理：系统pytest临时目录存在账户权限问题，改用新的项目内basetemp；需要缓存/Git/容器权限时经正式审批，不修改全局信任或清理系统临时目录。
- 本轮旧服务PID12852与两个专用测试容器已停止，命名卷和.local源副本/日志/备份保留；没有删除材料或旧数据卷。
- 下一项：Task2领域规则、配置、ID与规模门禁。v1尚未验收，保持v1分支，main未合并、无远端推送。
- 最终文档/工作区复核：20个Markdown、78个本地链接、0失效链接/围栏错误；AGENTS30行；旧后端与前端工作区均干净。Task1提交后以Git实际HEAD核验提交标识，不在提交内自引用SHA。

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

## 2026-10-28 · v1 Task 2：领域规则、配置、ID 与规模门禁

- 开始前HEAD：458f5528a3ce16020ab70661f2b84ceda0a19102，分支v1，工作区干净；本轮只执行计划Task2，未合并main、未推送。逐项需求与实现见 [阶段报告](../versions/v1/task-2-report.md)。
- 新增core配置/错误/时钟/ID类型与生成器；documents按领域数据、命令、纯文本规则、应用存储端口拆分，没有路由/SQL/Mongo实现。只建立本阶段需要的包。
- 对固定旧版编译产物做无需HTTP/数据库的纯方法探测，确认BOM/NEL/中文标点、UTF-16半代理摘要和worker0/1023别名行为。首次Snowflake探测使用模块对象而非default构造器失败，修正导入后取得真实向量；未改参考源码或历史快照。
- TDD：领域缺模块时2个收集错误→41通过；配置/ID缺模块时2个收集错误→32通过；检查器缺脚本时10失败→10通过。保留PATCH显式字段不可变快照；查询status任意整数与page范围分开；雪花回拨/序列耗尽失败且不修改已用状态。
- D016–D018记录文本编码边界、worker修正与显式配置加载；轻量identifiers防止核心反向依赖业务；.env.example从Task6提前。记录后续BSON必须替换U+FFFD、HTTP单独处理转义、部署worker唯一且无跨重启高水位保证。
- 实际完整测试：`.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task2-all-009 --cov=knowledge_hub --cov-report=term-missing` → **113 passed、1 skipped、0 failed**；跳过为未启用的旧库探针。当前src语句+分支覆盖96.68%，现有85%门禁通过，不代表未实现业务路径通过。
- 实际静态门禁：Ruff format最终只读60文件通过；Ruff check通过；mypy strict src/scripts 27文件无问题；文件门禁27文件，最长105/300行，新领域commands84行。300/301、末行、不同换行、坏编码、链接和缺目录均有测试。
- 单次独立只读代码审查：无Critical/Important/Minor；reviewer自行跑领域/配置/ID72通过、1项dotenv写文件测试未选中，格式/lint/行数/diff通过。完整测试/coverage/mypy由主执行者运行；没有需要修复或二次审查的问题。未验收边界逐项保留到Task3–7，不降低v1出口要求。
- 更新README、架构、规范、决策、契约、规格、计划、status与报告，下一项Task3：真实双库读取、迁移、BSON映射、锁及操作日志。仍无Python HTTP服务、差分、完整恢复/E2E/CI或v1验收。
- 本轮未启动任何HTTP/数据库服务；只读compose ps确认两个kh-fastapi-v1-test容器均Exited(0)，卷保留。旧后端与前端Git工作区均干净；未修改全局safe.directory、未触碰旧卷。
- 交接文档复核：20个Markdown、82个本地链接、0失效/围栏错误；AGENTS保持30行。本阶段本地提交信息：`feat(v1): add domain rules and core quality gates`；实际提交SHA在提交后用Git核对，避免文档自引用。Git差异复核后提交。

## 2026-10-28 · v1 Task 3：双库读取、迁移、锁和操作日志

- 开始前HEAD为8befa08758b21dc80559d06c9441573378fa7fe2，v1干净；只执行Task3。使用既有专属checkout与Windows账本；逐项需求/实现/证据见[阶段报告](../versions/v1/task-3-report.md)。
- 启动前核对两个kh-fastapi-v1-test容器均Exited(0)，随后compose up -d --wait均Healthy；未启动旧HTTP或删除卷。新测试固定本机专用端口/测试DB，再用UUID SQL schema和Mongo集合隔离。
- 新增SQLA Async/PyMongo Async客户端、SQL行/BSON记录、映射、读取仓储、读store、session文档锁、操作日志、冻结Alembic迁移与Mongo索引命令。保持原23列类型、默认值、null、ObjectId关联及字符串大ID；BSON边界与原044快照对比通过。
- TDD：缺客户端模块时读取/迁移及锁/日志测试失败；实现后首轮18项真实数据库测试通过。补20并发详情测试稳定复现共池饥饿（3秒超时），根因为持锁/等待锁耗尽查询所需池；分离lock_engine后通过，新增D019记录两池最多30连接/进程与双池关闭责任。
- 已验证升级/降级/升级与幂等、原列型/默认/唯一非空、无版本已有表拒绝、分页/组合过滤/ILIKE/软删除/缺正文、索引幂等/唯一、同文档串行/不同文档并行、锁异常/持有者取消/等待者取消/超时释放、prepared独立持久和metadata/completed同事务可见及回滚保护；共19项Task3真实库测试。
- 类型检查首轮发现过滤表达式列表推断过窄及BaseSettings的_env_file伪错误；补显式ColumnElement类型，并核对已安装官方Pydantic插件源码后启用pydantic.mypy，未添加宽泛ignore。初次迁移import排序问题已修正。
- 实际完整命令：KH_RUN_STORAGE_DB_TESTS=1、KH_RUN_LEGACY_DB_TESTS=1，`.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task3-all-007 --cov=knowledge_hub --cov-report=term-missing --tb=short` → **133 passed、0 skipped、0 failed**；当前src语句+分支95.10%，85%门禁通过。尚未实现的恢复/HTTP/E2E不记作通过。
- Ruff format只读85文件、Ruff check通过；mypy strict src/scripts/migrations 46文件通过；行数门禁44文件，最长105行；uv lock --check --offline解析45依赖通过；索引CLI --help与Alembic history入口通过。
- 只读审计临时SQL schema/Mongo集合均0残留。完整回归包含既有legacy探针按原流程重置专用public表/document_content合成数据；新测试不改原表结构，75快照与参考仓库不改。旧前后端Git工作区均干净。
- 单次独立只读审查无Critical/Important/Minor；reviewer实际核对源/测试、Ruff、52文件格式、BSON代理字符边界及staged diff，无需修复。133完整测试/coverage/mypy由主执行者运行，未冒称reviewer重跑真实库。
- README/status/规格/契约/架构/决策/计划/报告/日志已同步，下一项Task4。两个专用测试容器已stop并核对Exited(0)，卷保留。本轮提交信息`feat(v1): add storage reads migrations and operation journal`；最终SHA提交后由Git核对。完整v1仍implementing，无main合并或推送。
- 最终文档复核21个Markdown、88个本地链接、0失效/围栏错误；AGENTS保持30物理行。Git差异空白检查后执行本地提交。

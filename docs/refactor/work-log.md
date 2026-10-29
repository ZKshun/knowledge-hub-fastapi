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

## 2026-10-28 · v1 Task 4：创建/查询与可恢复创建

- 开始前HEAD：a7a28a4bf9fcfad70c7f2baa7aac1d94326484f3，v1干净；沿用专属checkout与Windows账本，本轮只做Task4。开始前113通过/20个未启用DB测试跳过；随后启动两个专用测试容器并确认Healthy，未启动旧HTTP/触碰旧卷。
- 逐项需求与证据见[Task4报告](../versions/v1/task-4-report.md)。新增独立创建/详情/分页用例、创建计划、日志行锁屏障、协调器、恢复服务；保留原接口/表列和字符串ID。store现有create/get/page/recover_pending，修改/软删除仍待Task5。
- TDD：用例缺模块RED→9通过；恢复实现缺失RED→16项真实双库故障通过。核对原042快照发现PyMongo接受空正文而Mongoose原创建报500，DID NOT RAISE测试RED→create-only校验GREEN；发布时间微秒123456与JS毫秒123000差异RED→GREEN。最终新增10项用例+17项双库测试。
- D020：prepared日志行FOR UPDATE从Mongo前持有至metadata/completed提交，恢复新session取得同一行锁后才核验SQL结果。验证旧SQL事务持续持锁时，新文档锁不能触发补偿；无法核验保留pending。异常失效旧session，普通错误向调用者抛出，不隐式重放创建。
- D021：创建补偿条件匹配_id/documentId/operationId/version，原子清空正文并保留空deleted/creationFence标记，不物理删除_id预留；真实唯一_id证明迟到insert失败。代价为少量持久内部行，不能自动清理/暴露为业务文档。未改历史75快照，后续差分须显式验证并排除内部标记，不能忽略所有deleted数据。
- 故障验证使用真实SQL/Mongo操作和测试内边界替换：Mongo前后、SQL提交前后模拟中断并新store恢复；SQL已提交但回包丢失、业务SQL新连接真实TCP拒绝、补偿失败/重试、取消、外部operation/version保护及迟到insert。没有声称执行OS kill或停整个PG服务器；范围在阶段报告明确。
- 实际完整命令：两个DB开关均1，`.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task4-all-010 --cov=knowledge_hub --cov-report=term-missing --tb=short` → **160 passed、0 skipped、0 failed**；当前src语句+分支覆盖95.05%，85%门禁通过。不代表未实现的Task5修改/删除或Task6HTTP验收。
- Ruff format最终101文件通过；Ruff check通过；mypy strict src/scripts/migrations 55文件；行数门禁53文件最长131/300行。初轮未用import/排序问题均修正。SQL/Mongo临时schema/集合审计0残留。
- 单次独立审查：1项Important（Python int与原PG BIGINT解析不等价）、无Critical/Minor。reviewer实际执行10项纯用例、只读PG转换探针与staged diff，未重跑修改库的完整测试。主执行者新增真实存储测试先7失败/4通过，修复为参数化Text→BIGINT SQL CAST，再增等价ID共锁；外键/操作者、路由/筛选/pending/锁均统一（D022），不只补写入一处。
- 最终完整命令同前，basetemp为task4-final-013 → **172 passed、0 skipped、0 failed，95.12%**；Ruff format103文件/检查通过，mypy strict56文件，行数54文件最长133行，uv lock --check --offline45依赖通过。只进行一轮审查修复，未冒称reviewer复核修复后代码。
- 最终临时SQL schema/Mongo集合0残留；两个专用测试容器均stop并核对Exited(0)，卷保留。README/架构/决策/规格/契约/计划/状态/报告/日志同步，下一Task5。参考前后端Git工作区干净；75原快照未改。提交信息`feat(v1): add recoverable document creation and queries`，实际SHA由Git核对，无main合并或远端推送。
- 交接文档复核22个Markdown、94个本地链接、0失效/围栏错误；AGENTS保持30物理行。最终Git差异空白检查后本地提交。

## 2026-10-29 · v1 Task 5：修改/软删除与完整恢复

- 开始前HEAD188c95a68007c40492b64c4f9b4903542cd4ba94，v1干净；继续专属Python checkout，未创建额外工作树。仅本Task5；基线123通过/49未启用DB测试跳过，随后启动既有两个专用容器Healthy，不启动旧HTTP或触碰旧卷。
- 需求与实现逐项对照见[Task5报告](../versions/v1/task-5-report.md)。新增update/delete应用用例，mutation_plan/writer、write_update/delete、content_mutations/recovery_mutations及恢复CLI，store完整满足DocumentStore。显式相同/空正文增版本，空PATCH/摘要/标题不增；发布转换/外部BIGINT原生CAST/缺正文/重复删除沿用原契约。
- TDD：用例缺模块2收集错误RED→16通过；store缺修改/删除11失败；恢复create-only15失败/6通过→完整32真实库测试通过；CLI缺脚本2失败→实现后独立子进程演练通过。强化实际pg_locks等待，并增外部operation/version保护、补偿自身中断、迟到写入器，专项22通过。
- D023：Mongo CAS绑定旧version/operationId；补偿恢复公开版本/正文/删除标志但设固定新rollback屏障，防旧在途CAS在版本回退后再次匹配。日志行锁仍是SQL事务已结束的证据，pending阻止详情/修改/删除；创建空creationFence仍保留，不物理清除。
- 首轮完整231通过、0跳过、94.86%。自查BSON合法NUL正文/摘要无法原样进入JSONB快照，2项真实库RED；单次独立审查确认同一Important，0Critical/0Minor。reviewer只读源/测试/legacy/决策，独立16单元测试及diff检查，没有执行数据库写入测试。
- 同轮修复：扩正文/摘要/删除/回滚4项均失败RED，D024使用UTF8→Base64内部快照、补偿严格解码，受影响40项GREEN，再补null/空串/Unicode摘要还原。可逆编码并非加密，仍需SQL权限控制；代价为快照文本约三分之一存储开销。未安排二次审查，修复后由主执行者完整验证。
- 最终实际命令：两个DB开关均1，`.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task5-final-015 --cov=knowledge_hub --cov-report=term-missing --tb=short` → **242 passed、0 skipped、0 failed、95.01%**，约91秒。新增16用例单元+54真实库/子进程/恢复/并发测试；完整包括原legacy探针，75份快照未覆盖。
- 最终Ruff format123文件/check通过；mypy strict src/scripts/migrations及比较器67文件通过；物理行64生产/脚本文件最长133/300；uv lock --check --offline解析45依赖。uv run --locked恢复CLI --help实测通过；CLI子进程真实恢复compensated=1/failed=0，再跑计数全0，冲突退出1且不输出正文，参数无效退出2。
- 故障验证为真实SQL/Mongo操作+测试内I/O边界替换；模拟中断/取消、新实例连接、已提交丢回包、真实业务TCP拒绝与活动旧SQL行锁。未声称OS kill、整PG重启/停机、网络分区或独立锁传输故障现场验证。HTTP/差分留Task6；CI/部署/生产访问/长期保留/完整验收留Task7及运营策略，不能据此声明v1可部署。
- 最终临时SQL schema与Mongo集合均0残留；两个kh-fastapi-v1-test容器stop后Exited(0)，卷保留，旧参考前后端Git干净。README/状态/架构/契约/规格/决策/计划/报告已同步，下一Task6。本地提交信息`feat(v1): add recoverable document mutations and recovery CLI`，SHA由Git核对；未合并main、未推送/发布。
- 交接文档复核23个Markdown、104个本地链接、0失效/围栏错误；AGENTS保持30物理行，计划工作目录保留供Task6–7接续。

## 2026-10-29 · v1 Task 6：FastAPI五接口与兼容适配

- 开始前HEAD abefa27b3f67a9da6ba821c5dadb023b2903d538，v1干净；沿用专属checkout，仅执行Task6。快速基线139项通过，再启动专用双库Healthy。逐项需求/实现/证据见[Task6报告](../versions/v1/task-6-report.md)，下一项Task7，未验收/合并v1。
- 五个/documents接口复用既有用例；DTO/映射/校验/查询数值/路由分文件，保留camelCase、字符串ID、POST201、分页、null和缺失、原错误顺序。app工厂/路由/lifespan/错误/OpenAPI/日志分职责；默认配置延迟到启动，Mongo和PG双池由AsyncExitStack关闭，main导出ASGI并支持PORT与显式--env-file。
- TDD：缺app模块RED→30项契约通过；入口/日志3项RED→35项相关通过；新差分模块缺失RED→原75项逐例真实双库HTTP重放全部通过。独立连续双库ASGI E2E补齐创建→读取→修改→软删除→404；8项负向比较器和内部标记实库测试防关联、精度/时区和删除正文被忽略。
- D025：新/变化时间先核验窗口、毫秒精度、时区和API→SQL关联再归一化，未变化字段严格比较；ObjectId按文档关联。仅071恢复原Mongo、073回滚SQL删除采用可靠性增强期望，074注入实际新补偿边界；原75份expected未改，业务deleted记录保留。代价为逐例隔离重放，连续路径另以E2E证明。
- 首轮完整372通过、0跳过、95.21%。补采固定原版真实HTTP证据，最终另存65项传输边界，保留请求字节/输入SHA/头/响应/编译身份；另存1份成功POST/GET及SQL/Mongo文本编码证据，未把新服务结果当expected。采集源固定Node22.23.2、旧v1 SHA及原compiledMain哈希，源进程都在各自finally停止。
- 单次独立只读审查：0Critical、3Important、0Minor，分别为Uvicorn重抛泄漏原异常、字节/字符集/压缩解析不兼容、JSON数字/字面量词法诊断不兼容。reviewer自行72项纯测试通过/2已知失败、3流式测试及真实Uvicorn协议内存transport验证，没有独立重跑完整双库。
- 同轮修复39失败/28通过RED→70项GREEN：SafeExceptionMiddleware消费未预期HTTP异常，真实TCP Uvicorn回归证明响应与普通日志不含私有sentinel；字符集校验→有界解压→解码→重放，100KB展开上限；JSON词法保留Node22消息/UTF-16位置，URL表单与路由HEAD等按原协议。D027–D029记录边界、脱敏及新增锁定Brotli1.2.1/精确SDK类型声明，代价为一个依赖和有界规范化成本，生产不依赖Node。
- 同轮自查未配对代理字符：原POST201而新500先RED；node_utf8_string统一Node pg/BSON替换，五类SQL文本和PATCH读回验证，68相关项GREEN。显式dotenv入口2项RED→CLI/lifespan6项GREEN。D026保留默认惰性配置和显式Settings注入；正式命令干净安装整体实测留Task7。
- 最终实际命令：KH_RUN_STORAGE_DB_TESTS=1、KH_RUN_LEGACY_DB_TESTS=1，`.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task6-final-026 --cov=knowledge_hub --cov-report=term-missing --tb=short` → **444 passed、0 skipped、0 failed，94.85%**，196.71秒。源码冻结后只更新文档，未为文档重复完整测试。
- 最终静态复核：Ruff check/format170文件、mypy strict src/scripts/migrations及比较器94文件、生产/脚本91文件最长137/300行、uv lock --check --offline46依赖均通过。无宽泛ignore或行数豁免；历史75快照diff为空。
- 审查范围/代价已保留报告与账本：修复后未二次审查；真实TCP测试针对服务器日志，双库E2E为ASGI；有限传输语料不代表所有畸形HTTP组合。CI、干净安装/正式启动、最终验收仍Task7；OS kill/网络分区与部署演练未执行，不作生产就绪承诺。
- 最终只读审计临时SQL schema/Mongo集合0残留；两个kh-fastapi-v1-test容器stop后均Exited(0)，卷保留。参考后端main b4dc6b2、前端v12 14ae352均干净，不修改旧代码/数据卷。AGENTS/README/架构/决策/规格/契约/计划/状态/报告同步，保存本地v1阶段提交`feat(v1): expose compatible FastAPI document endpoints`；实际SHA由Git核对，无main合并/remote推送。
- 交接文档复核24个Markdown、115个本地链接、0失效/围栏错误，AGENTS保持30物理行；git diff --check通过。计划工作目录保留供未完成Task7接续。

## 2026-10-29 · v1 Task 7：CI、干净环境与验收（执行中）

- 起点v1 HEAD `b9075b66790b94a537a16e3f14a37a93aaf8ab97`、工作区干净；复用同一独立Python仓库。逐项需求/实现/结果已写入[验收记录](../versions/v1/acceptance.md)，合并前仍为verifying。
- 发现测试Compose从忽略的`.local/legacy-v1`挂原版init.sql，干净克隆无法初始化public对照表。新增字节一致的`tests/fixtures/legacy_v1/postgresql/init.sql`，manifest SHA f3f94d...原值不变；缺文件契约RED→1项GREEN。Compose改挂版本化夹具；本轮全新Compose卷实测原版表23列/0行。D030记录复制测试DDL代价与CI来源。
- `.github/workflows/quality.yml`以只读权限、固定checkout/setup-uv版本、Python3.12、锁定安装/静态门禁、专用双库/全套测试和always停止容器组成；离线js-yaml解析7步骤和push/PR触发、Docker Compose config均通过。当前无remote，云端Actions未运行。
- 反向门禁：300/301文件规模10项通过；忽略目录内故意返回类型错误使mypy退出1，故意把字符串ID换数字使契约pytest退出1并准确报告`$.id`类型；不改变正式证据。
- 全新`.local/task7-venv`按uv.lock安装46依赖；Ruff格式170文件/check通过、mypy strict94文件、生产/脚本91文件最长137/300、离线锁检查46依赖通过。
- 用本轮新建的`kh-fastapi-v1-acceptance`项目提供隔离PG16/Mongo7，回环55432/57017；完整命令两个DB开关均1，`uv run --locked pytest tests/unit tests/integration tests/contract tests/e2e -q --basetemp=.local/pytest-runs/task7-full-001 --cov=knowledge_hub --cov-report=term-missing --cov-fail-under=85` → **445 passed、0 skipped、94.85%**，177.55秒。输出`.local/task7-full.log`，历史75快照未改。
- 另建空`knowledge_hub_fastapi_app_test`只供正式运行：Alembic upgrade→base→head，23列/版本0001；Mongo索引命令两次成功、documentId_1唯一；恢复CLI在空队列与HTTP更新/删除后均输出completed/compensated/failed全0。
- 正式`.local/task7-venv/Scripts/python.exe -m knowledge_hub.main --env-file .local/task7-app.env`监听127.0.0.1:38121；OpenAPI/docs200，创建201、列表/详情/修改/删除200、删除后详情404；真实PG标题/deleted/content_id与Mongo正文/version2/deleted/ID关联吻合。本轮启动器与日志中的服务PID均已消失，38121不再监听。配置/探针在忽略的.local，不入提交。
- 测试夹具的临时SQL schema/Mongo集合最终只读审计各0。参考旧后端/前端只读、旧卷不动；本轮新验收容器保留运行供合并后完整回归，审查结束再停止。README按实测顺序加入安装→独立空库→迁移/索引/恢复→正式启动→验证/停止，质量规范/契约中过时的Task6待办同步更正。
- 尚待：合并前全分支审查、最终文档/敏感数据/链接审计、Task7提交及验收状态、按既有授权本地main合并和合并后回归。CI云端运行、OS kill/网络分区与已有业务库baseline/导入不在本次实测范围，不作这些结论。
- 中途文档复核25个Markdown、123个本地链接、0失效/围栏错误；AGENTS30物理行，git diff --check通过。阶段提交后进行全分支独立审查，验收状态保持verifying。
- 合并前独立只读全分支审查基准main `5e43438`→Task7阶段提交`50e8da7`：0Critical、1Important、1Minor。根级方括号表单键静默丢弃会把原400变新201；数字未知键错误顺序原400 body不同。因用户要求精确接口兼容，将后者上调Important，固定旧NestJS编译身份后采集3表单+3 JSON/查询无效请求；对应契约分别RED→GREEN。原65传输样本逐项未变，补充证据累计71；原75双库expected不变。审查后未二次独立审查，七项未独立判断的范围与处置见[验收记录](../versions/v1/acceptance.md)。
- 修复后表单解析拆出根级键辅助函数以满足圈复杂度≤10；Ruff格式171文件/check、mypy strict94文件、生产/脚本91文件最长137/300、uv离线锁46包均通过。最终代码完整双库/契约/E2E`task7-final-code-002` → **451 passed、0 skipped、94.71%**，180.64秒；此前一次边测试边拆函数的中间回归451/93.89%不作最终源码证据。最后SQL临时schema/Mongo集合各0，旧/新服务3101/38121均无监听。
- 文档/差异审计：25份Markdown、124个相对链接0失效、围栏成对，AGENTS30行，`git diff --check`通过。`docs/versions/v1/acceptance.md`逐项需求→实现→证据已标accepted；当前v1尚未合并main，无remote/云端CI/推送/发布。下一步仅保存最终本地提交并按既有授权合并main、核对SHA和关键回归，之后标merged；不启动v2。

## 2026-10-29 · v1 本地合并与交接

- v1验收修复提交`75f62ed639f784cac5c2e039ac9afcb622327aa5`保存后工作树干净；其merge-base与原main均为`5e43438`。切换main，执行既定`git merge --no-ff v1 -m "merge: integrate v1"`，得到合并提交`d1d4a2703d6be62a4ce11efad9627fe874e897a6`，两亲分别为原main和v1；合并树与v1提交树均为`cfd0081eef5c68a4558b018315244899cbacdf84`。
- 合并后两个DB开关均1，`tests/contract tests/e2e`关键回归`task7-post-merge-001`实际197 passed、0 skipped，50.66秒；输出位于忽略的`.local/task7-post-merge.log`。最后停止本轮`kh-fastapi-v1-acceptance`两个专用容器，均Exited(0)；原`kh-fastapi-v1-test`同为Exited(0)，卷均保留。没有remote、推送、PR、标签或发布，云端CI未运行。
- v1验收记录、计划、状态更新为merged，保留v1分支；下一版本v2尚未开始，必须从更新后的main派生。文档交接提交将使main HEAD高于合并SHA，新会话先核对Git再按status继续。
- 合并后文档审计25份Markdown、126个相对链接0失效/围栏错误；AGENTS30行，`git diff --check`通过。文档提交不改受验收的Python源码树；合并后197项测试已在交接文档修改前运行，修改内容仅为状态与证据。

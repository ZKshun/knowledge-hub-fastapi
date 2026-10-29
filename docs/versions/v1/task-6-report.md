# v1 Task 6：需求与实现对照

日期：2026-10-29；分支v1；开始前HEAD：`abefa27b3f67a9da6ba821c5dadb023b2903d538`。实现、单次独立审查修复和最终回归完成；本地提交以Git核对。完整v1仍待Task7验收，不合并main或推送。

## 完成哪些需求、如何完成

| 需求 | 实现方式与位置 | 实际验证 |
| --- | --- | --- |
| 五个文档HTTP接口 | documents/api/router仅编排五个既有应用用例，requests/responses/mappers分开；不直接返回ORM | POST201、GET分页/详情、PATCH、DELETE→404完整路径；camelCase、字符串ID、23列元数据、列表不含正文、null字段保留 |
| 原版请求与错误 | 自定义校验保留Nest字段/约束错误顺序；JS Number查询转换；应用错误映射400/404/500，不返回默认422/detail | 原版缺失/null/未知字段/枚举/布尔/分页/异常ID差分；额外多错误、重复查询值、0x/0o/0b/指数、枚举标签与bool区别 |
| HTTP解析兼容 | transport/body_reader/json_errors/json_tokens/form_body与HTTP解压适配分开；大小写/单尾斜杠、HEAD、原OPTIONS404 | 65份另行补采的固定原版真实HTTP证据全部比较；非法/root/nonfinite JSON、UTF-16位置、数字/字面量、表单、原型键规则 |
| 字节、字符集与压缩 | 先校验字符集，再gzip/deflate/br有界展开、解码并重放规范化JSON；100KB按展开正文计；1000表单参数/32层限制 | UTF-8替换、BOM、UTF-16/32、未知charset415、压缩/损坏/截断、超限413；流式超过上限提前停止读取，断连不进入业务 |
| SQL和Mongo文本一致 | node_utf8_string复现Node pg/BSON未配对代理字符替换；保留POST/PATCH原输入、GET持久化读回差别 | 新增固定原版POST/GET及选定SQL/Mongo证据；原版POST201而新500先RED，修复后标题/摘要/封面/标签/备注及修改读回通过 |
| 生命周期和配置 | create_app支持显式Settings/存储注入；默认配置延迟至lifespan，AsyncExitStack关闭Mongo与PG双池；启动ping，不自动DDL/恢复 | 导入不构造配置/客户端；正常、启动失败、应用异常时实际客户端关闭，关闭后Mongo调用失败，双池无借出连接 |
| 启动入口与API文档 | 导出knowledge_hub.main:app；CLI读取PORT默认8000，显式--env-file；同一Settings传入ASGI；OpenAPI展示查询与400错误 | CLI参数先RED→GREEN，--help实测；查询7字段/分页边界文档、无错误422文档；真实TCP Uvicorn测试另验证服务器层 |
| 普通日志不泄漏正文 | RequestLoggingMiddleware记录方法/状态/耗时/请求ID，不记录body/query；SafeExceptionMiddleware消费未预期HTTP异常 | 真实Uvicorn TCP测试先证明原异常sentinel出现在普通traceback，再修复为仅异常类型；响应脱敏500，请求ID一致且上下文释放 |
| 新旧差分和闭环 | tests/support隔离夹具/状态/比较/执行分文件，旧75份证据哈希不改；另有连续真实双库ASGI E2E | 原75项逐例通过；8项负向比较器防漏判、内部标记单独证明；创建→列表→详情→同正文/摘要/空PATCH/发布→删除→404 |
| 可接续与质量 | 更新AGENTS、README、状态、规格、契约、决策、计划及本报告 | 最终444通过、0跳过，src语句+分支94.85%；strict94文件、91生产/脚本文件最长137/300行，Ruff及46包锁通过 |

## 差分执行与允许的变化

75份原证据仍在tests/fixtures/contracts/v1，manifest与所有文件未改。每例在新SQL schema和Mongo集合中恢复原版前一快照，再执行相同请求，避免原版异常残留污染后面的比较。028显式移除缺失正文、075显式建立并列时间，与原采集动作一致；另有连续新服务生命周期测试，不把独立用例重放冒称连续完整运行。

注入原证据的生成文档ID，仍保留字符串和完整关联；真实Snowflake接入由E2E与既有ID测试覆盖。新ObjectId只按documentId和新增记录建立绑定，SQL content_id、Mongo _id、响应contentId须一致；已有ID不可变。未变化时刻逐字比较，仅新/变化时间按实体和字段归一化，要求精度/时区表示不变、落在请求窗口，并验证HTTP时间等于SQL毫秒序列化。075只允许相同createdAt组内换序，其他顺序严格。

仅两项原缺陷状态有明确可靠性期望：071 SQL更新失败后恢复原Mongo正文/版本；073 Mongo删除失败后SQL删除回滚。其余业务字段严格比较，HTTP状态/body仍与原版比较。074将原删除补偿故障换到新实现实际使用的Mongo update补偿边界，证明compensation_pending、脱敏错误和恢复重试，而非复制无法发现的孤儿正文。

Mongo operationId/rollback标记须先验证UUID、对应日志、documentId和content_id。只有空正文/空摘要/长度0/version1/deleted/无SQL元数据且日志已补偿的creationFence才可排除；正常软删除正文保留并比较。负向测试证明错误内容、丢失删除正文、错误contentId关联、时间精度/时区/持久化关联变化均不能被归一化掩盖。

## 补充证据及复现

- `tests/fixtures/contracts/v1-http-boundaries.json`：65项固定原版真实HTTP响应；每个输入保留rawBody、rawBodyHex或可重建rawBodySpec及SHA256，含Content-Type/Encoding。全部为不会通过业务校验的请求或读取，源数据不变。
- `tests/fixtures/contracts/v1-text-encoding.json`：一次原版成功创建/详情与该文档SQL/Mongo编码状态；采集后已通过原API软删除唯一自建文档。
- 二者均记录固定sourceCommit、原manifest同一compiledMainSha256、Node22.23.2和日期；与原75份分开，未使用新服务输出作为expected。
- 原版隔离构建/启动按[基线复现](contract-baseline.md)，固定3101及专用测试库。重放补充证据时从请求定义构建字节、核验输入SHA、发送相同头/body并重新采集响应；不得覆盖旧expected。原始本轮输出和一次性探针在忽略的.local内，独立克隆可由版本化输入定义重新发送，无需聊天历史。

本轮启动的原版补查PID45676/19584/26900/50728/45152均在各自命令finally中停止；未切换或修改参考仓库，不使用旧volumes。

## 审查与修复证据

独立只读审查：0 Critical、3 Important、0 Minor。reviewer自行执行72项纯测试/2项已知失败及3项流式测试；用真实已安装Uvicorn协议代码+内存transport确认原异常会外泄；用固定Node/body-parser验证词法、gzip和UTF-16。没有启动服务、修改数据或独立重跑75项真实库与完整覆盖率。

| 发现 | 失败证据 | 本轮修复及验证 |
| --- | --- | --- |
| Uvicorn仍输出未预期异常原消息 | 真实TCP Uvicorn隐私测试泄漏PRIVATE_UVICORN_SENTINEL | 应用内消费脱敏异常，阻止外层ServerErrorMiddleware重抛；真实服务器普通日志及500响应不含sentinel |
| 解码/字符集/压缩不同 | UTF8/latin-1两项RED；扩展固定原版字节/压缩/表单探针 | charset→有界解压→解码→重放，保留UTF替换和JS Number；HTTP适配层隔离SDK，精确类型声明无宽泛ignore |
| JSON数字及字面量诊断不同 | 1e、1e+、负号、末尾小数点、tru/fal/nul等原版HTTP期望 | 独立词法扫描和UTF-16位置；不在生产调用Node；字段校验与JSON语法错误保持不同message类型 |

扩展回归整体先39失败/28通过，修复后70项通过；后续自查SQL文本编码1项RED→GREEN，相关68项通过；显式dotenv入口2项RED→CLI/lifespan6项通过。所有审查和自查问题在同一修复轮处理，最终完整444项回归通过；没有二次审查，不声称reviewer复核修复后实现。

br兼容新增并锁定Brotli1.2.1；选择依据为[官方版本说明](https://github.com/google/brotli/releases/tag/v1.2.1)和[官方Python实现](https://github.com/google/brotli/blob/v1.2.1/python/_brotli.c)。使用process输出限制并持续核对展开长度；SDK未提供类型的实际调用边界在typings/brotli.pyi精确声明，经真实压缩请求验证。代价为一个依赖和有限的解码/规范化成本；生产不依赖Node。

## 实际验证结果

| 验证 | 结果 |
| --- | --- |
| 开始前unit/contract快速基线 | 139 passed |
| 首批HTTP/入口/日志 | 30/35通过；未配对代理字符测试客户端先改为ASCII转义原始JSON，避免HTTPX先失败 |
| 原75项真实库逐例重放 | 75 passed，约47秒 |
| 首轮完整task6-full-015 | 372 passed、0 skipped，95.21% |
| 原版传输初扩展 | 20 failed/3 passed→64相关通过；之后字节补充2 failed/23 passed |
| 审查修复task6-review-red-020→green-021 | 39 failed/28 passed→70 passed，含真实TCP服务器 |
| SQL文本task6-pgtext-red-022→green-023 | 原500而应201 RED→68相关通过 |
| 最终task6-final-026 | **444 passed、0 skipped、0 failed，94.85%**，约197秒 |
| Ruff check / format --check | 最终复核全部通过，170文件格式一致 |
| mypy src scripts migrations tests/contract/comparison.py | strict，94 source files通过 |
| check_file_limits.py | 91生产/脚本文件，最长137/300行 |
| uv lock --check --offline | 46依赖解析通过，Brotli1.2.1已锁定 |

最终命令（专用Compose双库先启动，两个开关均1；再次执行需换新的basetemp）：

```powershell
$env:KH_RUN_STORAGE_DB_TESTS='1'
$env:KH_RUN_LEGACY_DB_TESTS='1'
.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task6-final-026 --cov=knowledge_hub --cov-report=term-missing --tb=short
```

## 运行入口与接续边界

```bash
uv run --locked python -m knowledge_hub.main
uv run --locked python -m knowledge_hub.main --env-file .env
```

入口支持PORT，默认127.0.0.1:8000；ASGI导出knowledge_hub.main:app；Swagger在/docs，schema在/openapi.json。没有隐式读取.env；显式文件仍遵守进程环境优先。数据库须先完成显式迁移/索引，启动不自动修改表、导入旧数据或执行恢复。主入口参数和--help已验证，按README从干净安装到迁移/正式命令监听的整体实测留Task7；实际TCP测试本轮针对日志与协议，真实双库E2E使用ASGI。

审查未判定项由执行者保留：完整库测试/覆盖率以本会话输出为据，不能冒称reviewer复现；reviewer内存协议验证另由本会话真实TCP测试补齐；有限证据不等于穷尽JSON/Unicode/头部/畸形HTTP所有组合；修复后代码与最终文档无二次审查；CI、干净安装/部署、OS kill/网络分区、完整验收与main合并属Task7或运维演练。代价是这些范围仍需后续验证，不作生产就绪承诺。无延后Minor。

最终只读资源审计：临时SQL schema/Mongo集合均0残留；专用两个测试容器已stop并核对Exited(0)，卷保留。参考后端main b4dc6b2、前端v12 14ae352工作区均干净；历史75份快照无改动。AGENTS/README/规格/契约/决策/计划/状态/工作日志已同步，阶段提交信息`feat(v1): expose compatible FastAPI document endpoints`，实际SHA使用Git查询。

文档复核24个Markdown、115个本地链接，0失效/围栏错误；AGENTS保持30物理行，git diff --check通过。

下一项仅Task7：CI、干净环境和实测运行说明、完整验收/交接，按既有授权验收后本地合并main；此前不创建v2、不推送或发布。

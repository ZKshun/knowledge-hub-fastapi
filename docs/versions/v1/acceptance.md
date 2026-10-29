# v1 文档服务验收记录

- 日期与执行者：2026-10-29，Codex；状态：**verifying，合并前审查待完成**。
- Python分支：`v1`；Task7开始前HEAD `b9075b66790b94a537a16e3f14a37a93aaf8ab97`；本轮工作树内容通过下述命令验证。阶段提交及合并SHA以后续Git记录为准，不能自引用尚未产生的提交。
- 来源：NestJS v1 `f9dfce20ffe798dc35ede0a74219f06bf3d6980f`；Python起点main `5e43438819bb660612799983c6af52bdef99941e`。
- 依据：[规格](spec.md)、[计划](../../superpowers/plans/2026-10-28-v1.md)、[契约](../../contracts/v1.md)、[决策](../../refactor/decisions.md)。
- 环境：Windows、Python3.12.14、uv0.12.15、锁定46依赖；全新`.local/task7-venv`；本轮全新`kh-fastapi-v1-acceptance`专用PostgreSQL16/Mongo7容器、回环端口55432/57017，旧参考仓库只读。

## 需求→实现→证据→结果

| 本版需求 | 实现方式与关键位置 | 实际证据 | 结果 |
| --- | --- | --- | --- |
| 固定原版基线和差分依据 | Task1采集器/比较器保存75份HTTP及双库原始状态和manifest哈希；Task7把固定原版建表SQL作为独立测试夹具，sha256继续对照manifest，Compose不再依赖.local | 75份证据哈希和逐例重放；新夹具缺失RED→哈希GREEN；全新卷初始化原表23列/0行 | 通过 |
| 领域规则、配置和ID | Task2 documents/domain、core/config、ids/clock保持JS字数/UTF-16、字符串雪花ID、显式Settings；文件门禁扫描src/scripts | 300/301负向测试10通过；全套单元/契约，配置/ID边界；生产文件最长137/300行 | 通过 |
| 多数据库与迁移 | Task3 PG元数据、Mongo正文、独立业务/锁池、日志行与Alembic，原23列保留；原SQL夹具只用于测试源结构 | 新原版测试库23列；另建空应用库Alembic升级→降级→升级后23列、版本0001；Mongo索引命令两次成功，documentId_1唯一 | 通过 |
| 创建、查询和失败恢复 | Task4应用用例、prepared操作日志/SQL行锁屏障、条件补偿及空creationFence；不自动清除内部标记 | 原75项逐例HTTP/双库差分、真实库故障/重启恢复用例、连续E2E；071/073状态改进按D025核对 | 通过 |
| 修改、软删除、并发和恢复命令 | Task5写入CAS匹配version/operationId、rollback新屏障、NUL安全快照、独立恢复CLI | 完整真实库并发/补偿/丢回包测试；本轮CLI空队列和正式HTTP更新/删除后再运行均输出completed/compensated/failed全0 | 通过 |
| 五个HTTP接口和原协议 | Task6 documents/api与app分层；校验/错误/JSON/表单/压缩/字符集、Uvicorn脱敏日志和生命周期；PG/BSON边界统一Node文本编码 | 原75项双库差分、另65项传输固定HTTP、1份SQL文本证据；本轮正式进程POST201、列表/详情/PATCH/DELETE200、删除后404，SQL/Mongo关联/version/deleted一致；OpenAPI/docs200 | 通过 |
| 工程门禁、CI和实测运行 | Task7版本化原SQL夹具、固定GitHub Actions/uv版本的只读质量工作流、README完整安装/初始化/启动/测试/清理命令 | 全新环境锁定安装46依赖；Ruff170文件、mypy strict94文件、行数91文件最大137；全新双库完整445项0跳过、94.85%；正式CLI真实TCP及双库验收 | 本地通过；云端CI未运行 |

## 命令与实际结果

| 命令/动作 | 实际结果 |
| --- | --- |
| `UV_PROJECT_ENVIRONMENT=.local/task7-venv uv sync --locked --all-groups --link-mode=copy` | 退出0；全新环境安装46依赖 |
| `uv run --locked ruff format --check .` / `ruff check .` | 退出0；170文件格式一致，lint无问题 |
| `uv run --locked mypy src scripts migrations tests/contract/comparison.py` | 退出0；strict94文件无问题 |
| `uv run --locked python scripts/check_file_limits.py` / `uv lock --check --offline` | 退出0；91文件最长137/300行，锁解析46依赖 |
| 两个DB开关均1的`uv run --locked pytest tests/unit tests/integration tests/contract tests/e2e -q --basetemp=.local/pytest-runs/task7-full-001 --cov=knowledge_hub --cov-report=term-missing --cov-fail-under=85` | 退出0；**445 passed、0 skipped、94.85%**，177.55秒；完整输出保存在忽略的`.local/task7-full.log` |
| 300/301行、mypy错误返回类型、契约把字符串ID变数字的反向门禁 | 行数10项通过；故意错误类型mypy退出1；故意错误契约pytest退出1且准确指出`$.id`类型不符；临时输入位于忽略的`.local/task7-negative` |
| 全新Compose卷及独立空应用库 | 原测试库`kh_document`23列/0行；应用库Alembic升级→降级→升级后23列、版本0001；Mongo两次索引初始化成功；CLI恢复空队列计数全0 |
| `.local/task7-venv/Scripts/python.exe -m knowledge_hub.main --env-file .local/task7-app.env` | 正式进程启动成功；真实回环TCP五接口、Swagger/OpenAPI、PG与Mongo状态/关联通过；仅本轮进程停止，38121无残留监听 |
| 全量后资源检查 | 临时SQL schema与Mongo集合各0残留；合成应用库索引`documentId_1`唯一，恢复队列全0 |

## 差异、审查与保留边界

- API/body/状态码、两库业务字段与原固定样本严格比较。071原版更新SQL失败遗留新Mongo正文、073删除Mongo失败却保留SQL删除，按D011/D025改为恢复一致；074在新实现实际补偿边界验证待恢复及重试。仅合法内部operationId/rollback与经断言的空creationFence可排除；业务软删除正文仍完整比较。75份原expected未修改。
- Task6独立审查0Critical、3Important、0Minor；Uvicorn异常日志泄漏、字节/字符集/压缩和JSON词法已在同轮RED→GREEN并完整444项回归，未二次审查。Task7合并前全分支独立审查待记录。
- 真实库故障测试覆盖连接拒绝、提交回包未知、补偿失败、中断和并发锁；未进行操作系统kill、整库停机、网络分区或生产环境演练。此范围不作为可部署生产保障。
- 当前Python仓库无remote。CI工作流已编写且本地等价命令通过，云端Actions未运行、无推送、PR或标签；不能把本地结果写作云端通过。
- 原版已有无版本业务表的实际切换仍需要独立审核的baseline/导入方案；v1空库迁移明确拒绝无版本旧表，服务启动不会隐式迁移。

## 集成与交接

- 本地Task7阶段提交：待创建；全分支审查：待完成；本地main合并：**未合并**。
- 用户已授权逐版验收通过后本地合并main；没有推送/发布授权。v2只能从合并后的main派生。
- 下次操作以[当前状态](../../refactor/status.md)和Git核对；验收前不得把`verifying`改为`accepted`或`merged`。

# v1 Task 1 阶段报告：原版契约基线

日期：2026-10-28。范围仅为 Task 1，**不是整个 v1 的验收报告**。Python 文档 CRUD、双库恢复和生产质量门禁仍待 Task 2–7。

## 需求与实现对照

| 需求 | 如何完成 | 验证证据 |
| --- | --- | --- |
| 建立独立 Python 开发环境 | Python 3.12.14、uv、src 包布局；在 pyproject.toml 声明依赖和工具配置，uv.lock 锁定解析结果 | uv sync 安装成功；Ruff 检查通过；mypy strict 检查 13 个源文件通过 |
| 固定原版 v1 来源，避免混用当前 main 或旧 dist | 从 f9dfce2 导出独立源码，禁止 CRLF 转换；逐文件比对 Git blob 原字节；按原 pnpm 锁安装并重新构建 | manifest.json 记录源码、依赖锁、构建产物 SHA256 与实际运行版本 |
| 采集现有接口和完整文档闭环 | 隔离启动原 NestJS 五接口；执行创建、查询、修改、发布/归档字段、软删除、校验及异常场景 | 75 份真实 HTTP 请求/响应和操作后 PostgreSQL/MongoDB 快照 |
| 建立能发现兼容差异的工具 | 比较器区分数值/字符串/布尔、null/缺失、列表顺序；只替换显式动态值，保留 ID 关联、日期精度和时区写法，保留完整 raw 证据 | 单元测试覆盖严格比较、动态错误文本、时间格式和输入不变性；所有文件哈希及 raw→normalized 一致性通过 |
| 核实跨库失败和补偿边界 | 使用独立测试容器；非法 bigint 触发 SQL 失败，Mongo 一次性 failCommand 触发写入/删除失败 | 创建 SQL 失败后的补偿、更新 SQL 失败、删除 Mongo 失败和补偿自身失败都有真实状态快照 |
| 避免把同时间记录的偶然顺序当成契约 | 为两篇文档设置相同创建时间后真实 GET；专用断言只允许连续同时间组内交换 | 新增并列时间快照和 5 个比较器场景，跨组换序、改字段和缺字段仍被拒绝 |
| 每版说明做了什么及如何实现 | 新增 D015；AGENTS/SOP 明确用户汇报义务；验收模板增加需求、实现、验证对照 | 规则、决策、模板及本阶段报告共同保存；后续版本沿用 |

## 实际环境与验证

- Python 3.12.14；Node 22.23.2；pnpm 12.5.1。
- PostgreSQL 16.15；MongoDB 7.0.43；Docker 项目 `kh-fastapi-v1-test`。
- PostgreSQL 镜像 ID：`sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`。
- MongoDB 镜像 ID：`sha256:84c4a18b60a0e73d1577112b0a600b46cab477c64cfe0ff36d0647bbca055bd0`。
- 数据库映射仅回环 55432/57017；采集请求只访问 127.0.0.1:3101；测试数据库 `knowledge_hub_fastapi_test`。旧 bootstrap 本身默认监听 `::`，任务结束后停止该临时进程。

本次构建/运行证明：源码首次导出到新目录；Nest `compilerOptions.deleteOutDir=true`，本次重新构建清空并生成 dist。按原始字节再次导出后重新构建并重启，未使用旧参考工作区的 dist。

2026-10-28 本地 16:03:39 启动的 PID 12852，已通过 Win32_Process 核验 executable 为 `D:\lxs-software\nodejs\node.exe`，命令行为该程序加 `dist/main.js`；3101 监听归属同一 PID。启动命令显式指定 WorkingDirectory 为本仓库 `.local/legacy-v1`，PORT=3101、POSTGRES_HOST=127.0.0.1、POSTGRES_PORT=55432、POSTGRES_USER=kh_test、POSTGRES_DB=knowledge_hub_fastapi_test、MONGO_URI=127.0.0.1:57017 对应专用库、TZ=UTC、SNOWFLAKE_WORKER_ID=7，未加载真实 .env。工作目录/环境是启动调用的记录，不声称从 OS 再读取了进程环境。

Nest 日志在 UTC 08:03:42 启动成功；最终采集 manifest 时间为 UTC 08:32:34。每次请求返回的 ID/contentId 与专用库即时快照对应，进一步证明 HTTP 与目标数据库的关联。根路由 Hello World 单独不能作为来源证明。

实际通过的检查：

```powershell
.venv/Scripts/python.exe -m ruff format scripts tests src
.venv/Scripts/python.exe -m ruff check scripts tests src
.venv/Scripts/python.exe -m mypy src scripts tests/contract/comparison.py
$env:KH_RUN_LEGACY_DB_TESTS='1'
uv run --locked --link-mode=copy pytest -q --basetemp=.local/pytest-runs/task1-final-007
```

结果：**31 passed，0 skipped，0 failed**；严格类型通过；手写生产/脚本文件最长 105 物理行，均 ≤300。此阶段不声明已达到完整服务的 85% 覆盖率，也不声明 FastAPI 已与旧服务差分通过。

## 确认的契约细节

- POST 创建返回 201；五接口均保留原路径和 camelCase，字符串雪花 ID 超过 JS 安全整数仍为字符串。
- 显式 PATCH 相同正文，Mongo version 仍 +1；仅 title、空 PATCH 或仅 summary 不递增正文版本。
- 创建 title/content 为 null 返回 400；PATCH title/content/status/isPublic 为 null 的部分路径返回 500。不能用一套默认 Pydantic 规则直接替换。
- 空标题创建可成功；空正文创建 500，但把现有正文 PATCH 成空字符串可成功；纯空白正文创建成功。
- `status=` 查询转换为 0；未知整数 status 返回空列表；未知查询字段返回 400。
- 合法但不存在的 bigint ID 返回 404；非法格式或溢出 ID 返回 500。
- 正文缺失时详情 content 为空字符串；更新正文返回 400。
- UTF-16 截断可能在 Mongo 摘要中存为替换字符：199 个 a + emoji + tail 的 contentLength 为 206，摘要长度 203，尾部包含 `�...`。

## 旧版可靠性缺陷的证据

`067_create_postgres_failure`：Mongo 先成功、SQL 失败后，正文被删除，创建补偿有效。

`071_patch_postgres_failure`：Mongo 正文/版本已更新，但 SQL 元数据写失败；旧版没有回滚正文。

`073_delete_mongo_failure`：SQL deleted=true 已保存，但 Mongo deleted=false，API 返回 500。

`074_create_compensation_failure`：SQL 写失败且 Mongo 补偿删除也失败，留下孤立正文。

这些状态描述旧系统，不是要求新 Python 实现保留不一致。内部可靠性在 Task 4–5 按既定规格增强；外部契约差异另行记录。

## 执行调整与限制

- 沿用已经独立、干净的 v1 仓库，以 git archive 建旧版副本；如源码来源核验不符，必须重新采集，不能沿用未经证明的快照。
- Windows 使用等价的本地执行账本和项目内独立 pytest 临时目录；公开 status 与 Git 记录是跨会话依据，私有账本丢失不影响接续。
- 本轮范围是用户要求的下一步 Task 1；没有提前实现 Task 2–7。运行手册见 [契约基线复现](contract-baseline.md)。
- 采集脚本是串行开发工具，使用同步数据库探针；未来 FastAPI 运行时仍按异步架构实现。
- 测试端口、数据库名、HTTP 目标都有显式保护；采集会清空该专用测试数据库中的文档表/集合，不能用于真实运行库。
- 采集器拒绝覆盖已有输出；重复采集写新目录，更新正式夹具前完整备份旧采集。备份保留在忽略的 `.local/v1-first-capture-backup`、`.local/v1-before-tie-backup`。

独立审查提出一项 Important：缺少同时间排序证据。已先复现失败断言，再增加真实场景和只放宽组内顺序的比较器，完整回归 31/31 通过；没有未处理 Critical/Important 或延期 Minor。最终提交状态以 [工作日志](../../refactor/work-log.md) 为准。下一步为 Task 2：领域规则、配置、ID 与规模门禁。

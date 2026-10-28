# 原版 v1 契约基线复现

工具要求 Python 3.12、uv、Node 22、pnpm、Docker。下面是当前 Windows 开发环境的流程；操作限本项目 `.local` 副本与 `kh-fastapi-v1-test` 测试资源。Python HTTP 服务尚未实现，这里启动的是旧 NestJS v1。

## 1. 安装 Python 依赖并导出固定源码

在 Python 仓库根目录执行。参考仓库默认同级 `../knowledge-hub-backend`，也可用采集器 `--source-repo` 指定。

```powershell
uv sync --locked --all-groups --link-mode=copy
New-Item -ItemType Directory -Path .local/legacy-v1 -Force
git -c core.autocrlf=false -C ../knowledge-hub-backend archive --format=tar --output=../knowledge-hub-fastapi/.local/legacy-v1.tar f9dfce20ffe798dc35ede0a74219f06bf3d6980f
tar -xf .local/legacy-v1.tar -C .local/legacy-v1
Push-Location .local/legacy-v1
pnpm install --frozen-lockfile --ignore-scripts
pnpm exec nest build
Pop-Location
```

必须关闭此次导出的 autocrlf，采集器会按原 Git blob 逐字节验证 src、初始化脚本、package.json 和 pnpm-lock.yaml。源副本不得有真实 `.env`，也不得使用其他分支的 dist。

如果 Windows Git 报 dubious ownership，仅为具体命令加入 `-c safe.directory=<确切仓库绝对路径>`；不全局信任所有目录。开发过程中遇到的权限审批与项目业务授权不是一回事。

## 2. 启动隔离数据库和旧服务

```powershell
docker compose -f deploy/compose.test.yml up -d --wait --wait-timeout 60
$env:PORT='3101'
$env:POSTGRES_HOST='127.0.0.1'
$env:POSTGRES_PORT='55432'
$env:POSTGRES_USER='kh_test'
$env:POSTGRES_PASSWORD='local-contract-only'
$env:POSTGRES_DB='knowledge_hub_fastapi_test'
$env:MONGO_URI='mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test'
$env:SNOWFLAKE_WORKER_ID='7'
$env:TZ='UTC'
$env:NODE_ENV='test'
$legacyProcess = Start-Process -FilePath (Get-Command node).Source -ArgumentList 'dist/main.js' -WorkingDirectory (Resolve-Path .local/legacy-v1) -WindowStyle Hidden -RedirectStandardOutput "$PWD/.local/legacy-v1.stdout.log" -RedirectStandardError "$PWD/.local/legacy-v1.stderr.log" -PassThru
Invoke-RestMethod http://127.0.0.1:3101/
```

先核对 3101、55432、57017 没有占用；不要停止占用端口的未知进程。健康检查应返回 `Hello World!`，进程刚启动时可在有界时间内重试。`local-contract-only` 是专用本地测试凭据，不是现有业务库凭据。

MongoDB 只在测试容器开启 enableTestCommands，用于一次性失败注入。工具会恢复原初始化脚本的 documentId 唯一索引；这是隔离空库的准备操作，不是线上迁移方案。依据：[MongoDB failCommand 测试说明](https://github.com/mongodb/mongo/wiki/The-failCommand-fail-point)。

## 3. 采集和验证

正式夹具已保存在 `tests/fixtures/contracts/v1`。重复采集必须指定不存在证据的新目录，例如：

```powershell
uv run --locked --link-mode=copy python scripts/capture_legacy_v1.py --base-url http://127.0.0.1:3101 --output .local/v1-recapture-001
New-Item -ItemType Directory -Path .local/pytest-runs -Force
$env:KH_RUN_LEGACY_DB_TESTS='1'
uv run --locked --link-mode=copy pytest -q --basetemp=.local/pytest-runs/manual-001
```

采集器拒绝已有 JSON 的输出目录；只允许 HTTP 回环 3101、数据库回环 55432/57017 和 `knowledge_hub_fastapi_test`，拒绝连接查询参数覆盖地址。它会重置该专用测试库的文档数据，然后执行正常和失败场景。不要让多个采集器或数据库测试同时操作同一测试库。

manifest 包含固定 source SHA、源码/构建/夹具哈希、实际依赖版本和动态值绑定。每份记录同时保留原请求/响应、双库状态和归一化数据；日期 token 保留精度及 Z/offset/naive 格式。原始响应不因归一化修改。

完整现有测试应为 31 passed；基线含 75 个真实请求。相同时间分页使用单独断言，仅允许同时间组内部换序，不放宽其他列表顺序或字段比较。未设置 KH_RUN_LEGACY_DB_TESTS 时，真实数据库索引测试会明确 skip，其余离线证据/比较器测试仍可运行；不能把这种结果写成真实数据库测试通过。这里的测试通过不代表未来 FastAPI 已兼容。

## 4. 停止本轮资源

确认 PID 和 3101 端口归属后，只停止自己启动的旧版服务。若仍在同一 PowerShell 会话，可用启动返回的 `$legacyProcess.Id`；新会话必须重新核验，不复制历史 PID 直接结束进程。

```powershell
Stop-Process -Id $legacyProcess.Id
docker compose -f deploy/compose.test.yml stop
```

stop 保留本项目测试命名卷，便于之后继续；不删除旧 volumes 或其他 Docker 项目。证据生成后不依赖后台服务持续运行。

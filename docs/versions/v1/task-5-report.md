# v1 Task 5：需求与实现对照

日期：2026-10-29；分支v1；开始前HEAD：`188c95a68007c40492b64c4f9b4903542cd4ba94`。本阶段实现、验证及审查修复完成；最终本地提交由Git核对，完整v1尚未验收或合并。

## 需求、实现与证据

| 需求 | 实现方式与位置 | 验证证据 |
| --- | --- | --- |
| 文档修改且保持原语义 | application/commands/update_document独立纯变换，provided_fields一直传到write_update；锁内读取最新详情 | 同正文/空正文显式更新均version+1；空PATCH/标题/摘要不增版本；summary null清空，未传字段保留 |
| 发布和元数据兼容 | 非发布→发布设置毫秒精度发布时间；重复发布/归档保留旧时间；外部BIGINT字符串交PG原生CAST | 16项用例测试；真实库覆盖0x/0o/0b外键及等价路由ID，拒绝Unicode数字并恢复 |
| 双库软删除闭环 | delete_document返回document_id/deleted；write_delete在相同日志/事务框架下置SQL和Mongo deleted | 保留原正文/版本；详情和列表排除；重复删除、已删除文档更新抛原业务404错误；正文缺失仍可删除 |
| 可恢复修改与删除 | mutation_writer在文档锁内读最新值、prepared独立提交；持日志行锁执行Mongo CAS，SQL metadata/completed原子提交 | Mongo前后、SQL提交前后中断、新store恢复；真实SQL约束回滚；提交成功但回包丢失不误补偿；取消任务可恢复 |
| 提交未知时保留证据 | 沿用D020，恢复新事务拿日志行锁后才核对；无法取得SQL证据保留pending | 真实旧SQL事务仍持锁时恢复失败且保留已写正文；SQL已提交/未提交分别遇业务连接拒绝时不猜结果 |
| 防迟到CAS和删除复活 | D023：每次正文写入改变operationId；补偿恢复公开字段/版本，同时写新rollback屏障 | 真实重放旧CAS匹配0；后续成功更新不被旧恢复覆盖；已完成更新的恢复不能复活后来删除；恢复自身中断可幂等重试 |
| 并发不丢字段与版本 | 独立lock_engine文档锁，锁内读最新元数据再变换，CAS匹配version和operationId | 两个更新分别保留对方字段、version=3；两个方向的更新/删除竞争均不复活。通过pg_locks确认竞争者实际等待，而非仅依赖调度时机 |
| 补偿失败可重试且不泄漏正文 | 保留compensation_pending，last_error仅异常类型；get/update/delete先查pending；不覆盖外部标记/较新版本 | 补偿异常后读写拒绝，重试恢复；外部operationId/version冲突正文原样保留；CLI不输出私有正文 |
| 独立恢复命令 | scripts/recover_document_operations.py；显式配置/资源、批次1–1000，关闭双库客户端 | 子进程恢复中断记录compensated=1/failed=0，再运行计数全0；冲突退出1；参数无效退出2；stdout仅JSON计数 |
| NUL/Unicode与空值兼容 | snapshot_encoding将旧正文/摘要编码为UTF8/Base64，在补偿时严格解码，null独立保存 | 4项失败复现→修复；最终7项覆盖正文/摘要/删除、NUL回滚和null/空串/Unicode摘要精确还原 |
| 跨会话接续与质量 | 用例/写入计划/CAS/补偿/命令按职责分文件，入口保持精简 | 最终242通过、0跳过，覆盖95.01%；strict67文件、行数64文件最长133行 |

## 修改、删除和恢复协议

```text
文档session锁 → pending门禁 → 读取最新SQL/Mongo → 纯变换/删除计划
  → prepared独立提交（旧正文/版本/标记的受控快照）
  → 业务SQL事务：日志行 FOR UPDATE，要求仍prepared
  → Mongo CAS（_id/documentId/旧version/旧operationId）
  → SQL metadata + completed → COMMIT

异常：失效旧session → 退出原文档锁 → 新文档锁 + 新事务日志行锁
  completed且SQL关联匹配 → 保留成功结果
  pending且SQL仍是原元数据 → 条件恢复Mongo公开字段/版本
    同时设置 rollback:<operation_id>，再提交compensated
  SQL无法核验、旧事务仍持锁、Mongo外部标记/版本冲突 → 保持pending
```

补偿条件同时识别“旧请求尚未到达”“本次Mongo写已完成”“本次补偿已完成但SQL未确认”三种状态。不能把operationId恢复到旧值；否则公开版本回退后，旧在途请求可以再次匹配，造成丢失成功修改或复活已删正文。补偿中断重试使用固定rollback标记，既不重复增加公开版本，也不重新开放旧CAS。

无正文写入的元数据PATCH仍有SQL日志和事务，但不修改Mongo版本或标记。正文缺失时原版允许只改摘要/元数据并返回空正文，显式改content仍抛DocumentContentNotFound；删除缺失正文也成功。已有Mongo正文deleted=true而SQL未删除的异常状态，更新正文按缺失处理，删除保持其原有软删含义。

创建的空deleted/creationFence标记仍按D021保留，不物理清理。正常业务软删除保留原正文，不能在后续差分中把所有deleted记录一起过滤。Task6应验证内部operationId仅为合法操作UUID/rollback标记，再从业务字段差分中移除，创建标记另按_id/operation/version/空正文断言。

恢复快照含私有旧正文，只写受控SQL日志，不进入普通日志/CLI。BSON允许NUL而JSONB拒绝，已通过UTF8/Base64编码快照、恢复解码解决（D024）。这是可逆编码而非加密，仍受数据库权限控制，代价为快照文本约三分之一额外存储。创建恢复快照仍仅含content_id，原75份证据没有改动。

## 恢复命令

从项目根执行，默认SQL schema为public、Mongo集合为document_content。环境变量沿用现有配置，不隐式读取本地.env；需要文件时显式--env-file。

```bash
uv run --locked python scripts/recover_document_operations.py --limit 100
uv run --locked python scripts/recover_document_operations.py --env-file <明确配置文件> --limit 100
```

支持显式--schema和--collection，以选择已部署的资源或隔离演练资源。命令不会执行DDL、创建索引或清理数据卷。每批最多1000，默认100；重复执行至未决计数清空。单批failed>0退出1，应核查冲突/连接后重试，不能跳过pending直接继续写该文档。配置/连接等整批异常退出2，stderr只输出异常类名；参数错误由argparse说明。stdout只输出completed/compensated/failed，不能把未能读取日志伪装成全部0。

CLI子进程演练在独立knowledge_hub_fastapi_test中，传入当前测试随机schema与集合；不会连接旧业务库。未增加后台调度器，运维可按后续部署策略定时调用。

## 验证与审查

- 基线：123 passed、49个未启用DB测试跳过；随后启用两个开关运行全部真实双库/旧探针。
- 用例RED：修改/删除模块缺失，2项收集错误；实现后16通过。
- 存储RED：11失败（mutate/soft_delete缺失）；实现正常路径后10通过，余下BIGINT失败待恢复扩展。
- 恢复RED：15失败/6通过，原恢复服务仅支持create；加入修改/删除补偿后完整32项通过。
- CLI RED：缺脚本2失败；实现后CLI/并发共11通过，随后加强真实锁等待并补恢复自身中断/外部标记版本保护，专项22通过。
- 首轮完整：两个DB开关均1，task5-full-010，231 passed、0 skipped，src语句+分支94.86%；Ruff、strict66文件、行数63文件最长133/300、锁文件45依赖通过。
- 自查NUL快照：task5-snapshot-red-012，两项真实库均因JSONB unsupported Unicode escape sequence失败。单次审查确认同一Important（0 Critical/0 Minor），task5-review-red-013扩展正文/摘要/删除/回滚4项均失败；编码修复后task5-review-green-014受影响40项通过。再补null/空串/Unicode摘要还原，最终全量包含7项编码兼容测试。
- 最终task5-final-015：**242 passed、0 skipped、0 failed，src语句+分支覆盖95.01%**，约91秒。新增16项用例单元+54项真实库/CLI/恢复/并发测试；覆盖率不计测试/脚本或尚未实现的HTTP功能。
- 最终Ruff check/format通过（123文件）；mypy strict src/scripts/migrations及比较器67文件通过；物理行门禁64生产/脚本文件、最长133/300；uv lock --check --offline解析45依赖通过。CLI的uv run --locked帮助入口实测通过。

最终全量命令（PowerShell，专用Compose双库先启动；每次使用新的basetemp）：

```powershell
$env:KH_RUN_STORAGE_DB_TESTS='1'
$env:KH_RUN_LEGACY_DB_TESTS='1'
.venv/Scripts/python.exe -m pytest -q --basetemp=.local/pytest-runs/task5-final-015 --cov=knowledge_hub --cov-report=term-missing --tb=short
```

独立reviewer只读核对全部本阶段生产代码、固定legacy service、测试、决策，自己执行16项单元测试和git diff --check；没有执行修改数据库的测试。主执行者将已复现的NUL问题纳入同一轮修复，RED→GREEN和最终242回归由主执行者执行；未安排二次审查，不能声称reviewer复核修复后代码。

故障注入只替换测试中的真实Mongo/SQL I/O调用边界，生产类没有测试模式。中断用BaseException/协程取消及新实例/连接模拟，不冒称OS kill。PG不可用为新业务连接真实TCP拒绝，数据库服务器和锁池仍运行，不冒称整个PG服务器关闭。

审查未判定项及执行者处理：完整测试/覆盖率和真实故障/CLI结果以主执行者实际运行输出为据，不能算reviewer独立复现；OS kill、PG重启/故障转移、锁连接意外丢失和真实网络分区没有现场证据，不能扩大当前韧性保证；HTTP协议及完整差分留Task6；CI/部署/生产权限/长期快照保留与完整验收留Task7及运营策略，当前快照不自动清理；最终README/status/报告和修复由主执行者收尾，无二次审查确认。代价分别为缺少重复运行证据、部署故障演练仍需另做、接口兼容尚未验收、生产访问/容量/保留政策仍需明确，以及修复后仅有测试/门禁证据；不以此宣称v1已可部署。无延后Minor。

最终资源核对：临时kh_t3 SQL schema和Mongo测试集合均0残留；专用两个容器已停止，均Exited(0)，卷保留；没有启动HTTP或接触旧卷。旧前后端Git状态干净。README/状态/架构/契约/规格/决策/计划/日志同步，本轮提交信息`feat(v1): add recoverable document mutations and recovery CLI`，实际SHA由Git核对，无main合并/推送。

交接文档复核：23个Markdown、104个本地链接、0失效/围栏错误；AGENTS保持30物理行。计划工作目录保留，供未完成Task6–7接续。

## 尚未完成

Task6：FastAPI五接口、请求/错误适配、生命周期及75份原版HTTP/双库差分；Task7：CI/实测启动说明/E2E/完整v1验收。保持v1 implementing，未合并main或推送。新会话按[当前状态](../../refactor/status.md)直接开始Task6，不重复已完成阶段。

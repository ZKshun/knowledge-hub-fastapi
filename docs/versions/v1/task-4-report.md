# v1 Task 4：需求与实现对照

日期：2026-10-28；分支v1；开始前HEAD：`a7a28a4bf9fcfad70c7f2baa7aac1d94326484f3`。本阶段实现/验证及审查问题修复完成；完整v1未验收或合并，最终提交由Git核对。

## 完成哪些需求、如何完成

| 需求 | 实现方式与位置 | 本轮证据 |
| --- | --- | --- |
| 创建与查询用例职责分开 | application/commands/create_document与queries/get_document/list_documents，依赖Clock/IdGenerator/DocumentStore | 10项单元测试：默认草稿/私有、空summary不伪造、发布/归档、创建者复制、字符串ID、失败传播、详情404业务错误、原分页封装 |
| 兼容旧创建语义 | 标题空串仍允许；create-only正文必需校验模拟Mongoose；publish_time截断毫秒，SQL其他时间保留原列型 | 对照041/042原快照；空正文先错误成功RED再修复；发布时间123456微秒RED→123000微秒GREEN。空正文应由Task6映射原500，不能改成400 |
| 可恢复的双库创建 | write_create预分配ObjectId/operation UUID，prepared快照只含content_id；write_coordinator先独立prepare，再在日志行锁内写Mongo及SQL metadata/completed | 真实SQL/Mongo创建关联、原默认/null/版本、重复ID不覆盖、SQL或Mongo失败无活动孤立正文 |
| 提交结果未知不误删 | transaction_fence锁住日志行，从Mongo前一直持到SQL提交；异常失效旧session，重取文档锁及日志行锁，核验completed/metadata | 提交成功后抛响应丢失仍保留成功正文；旧SQL事务行锁仍持有时恢复超时且不补偿；恢复后查询正确 |
| PG不可用保持未决 | 无法取得新SQL证据即返回恢复failed并保留记录/正文；同文档创建门禁先检查pending | 将新业务SQL连接真实路由到不可连接的本机端口，分别测试SQL已提交/未提交；不可用期间不补偿且拒绝新写；恢复连接后幂等核对 |
| 补偿失败可重试且不泄漏正文 | recovery只记录异常类型，补偿失败保持compensation_pending；条件匹配原operation/version | 注入Mongo补偿异常，last_error仅OperationFailure；新写被阻止，重建store后恢复成功；其他operation/version2正文未被覆盖 |
| 防迟到写入 | 补偿原子替换/upsert空deleted创建标记，保留同一_id及operationId，creationFence=true | 模拟Mongo发送前中断，先恢复再重放旧insert，真实Mongo唯一_id拒绝；无活动正文 |
| 可观测的恢复结果 | store.recover_pending返回RecoveryReport(completed/compensated/failed)，每条独立锁/事务；恢复不改业务版本 | Mongo前后、SQL提交前后中断及取消任务；新store/新连接恢复；再次恢复计数0，不重复补偿 |
| BIGINT原生语义 | integrations/postgres/identifiers统一Text绑定后CAST BIGINT，不用Python int解析外部字段；路由/筛选/pending/锁键共用 | 审查1项Important：0x/0o/0b应成功，Unicode数字/NBSP应失败；12项真实库回归含BIGINT上下界、5外键/操作者字段和等价ID共锁 |
| 高质量与接续 | 映射、创建计划、事务屏障、协调与恢复分文件；同步架构/决策/计划/状态/报告 | 最终172项全部通过、无跳过；当前src语句+分支覆盖95.12%；strict类型56文件；54生产/脚本文件最长133/300行 |

## 创建及恢复协议

```text
生成UUID/ObjectId → 取得文档session锁 → 拒绝pending/重复ID
  → prepared独立提交（仅content_id快照）
  → 新业务SQL事务 SELECT operation FOR UPDATE，要求仍prepared
  → Mongo insert（原字段 + operationId）
  → SQL metadata + completed → COMMIT

普通异常 → 失效旧业务session → 退出原session锁
  → 新session锁 → 新SQL事务取得日志行锁（旧事务结束的屏障）
  → completed且metadata关联匹配：保留正文
  → pending且无metadata：条件替换为空deleted创建标记，标记compensated
  → SQL/锁无法核验或发现冲突：保留未决，不清除正文
```

写入器取得行锁后必须再次检查state，恢复改成compensated后迟到写入器不能继续。元数据存在但pending不符合正常原子提交不变量，恢复明确失败，不猜测删正文。单文档session锁与日志行锁职责不同，不能去掉后者，也不能将旧事务“结束”误判为仅本地invalidate调用返回。

创建补偿后的Mongo标记为空正文、contentLength0、contentSummary空、version1、deleted=true、creationFence=true，保留_id/documentId/operationId；存在其他operation或新version时upsert因唯一_id失败而保留原正文。该内部标记不进入普通详情/列表/HTTP，不自动清理；它避免在旧SQL事务已结束但旧Mongo请求仍在途时，物理删除后被迟到insert复活。保留少量内部行是D021明确记录的可靠性代价。

## 后续共享接口与边界

- create_document/get_document/list_documents签名沿用计划，内部不依赖FastAPI/ORM；最终HTTP适配仍属Task6。
- PostgresMongoDocumentStore现有get/page/create/recover_pending；尚缺mutate/soft_delete，不用成功空实现伪装完整DocumentStore。
- RecoveryService(postgres, collection, fence_timeout_ms=5000)提供recover_one及有界recover_pending；若pending列表本身不可读则抛SQL错误，不能返回伪造0失败。逐条无法核验返回failed，保留未决状态。
- 普通创建异常仍向调用者抛出；即使确认SQL已提交也不隐式重放创建。CancelledError和模拟进程中断不执行在线补偿，由新实例恢复。
- transaction_fence.lock_operation只在当前session事务持锁；写入器持有至commit/rollback，恢复持有到核验/补偿提交。查询日志状态不锁行不能替代该证明。
- mark_completed仍使用调用者SQL事务；快照不保存创建正文。last_error只存异常类名，不存驱动原始消息或正文。
- Task5必须保留创建标记，并为修改/删除的迟到写、条件版本与恢复另做证明；不能仅恢复公开version后重新接受旧在途CAS。发布时间继续毫秒精度；PATCH空正文允许，不能复用create-only校验。
- source042空正文创建为500，source026空正文PATCH可成功；Task6需分别适配。成功POST仍返回原输入content，GET读取BSON编码后的正文，不能混淆两者。
- bigint_parameter只生成参数化SQL表达式，外部字符串由PostgreSQL解析；0x10读回为16，１２/١٢/NBSP和溢出按PG失败。锁键也用同一PG规范化，代价为每次取锁增加一次SQL规范化往返；不能把查询/写入修好了却仍按Python转换锁键。规范十进制内部ID与生成器不受此规则影响。

## 验证方法与实际结果

使用既有专用容器及Task3测试schema/集合夹具。SQL/Mongo的写入、提交、行锁、唯一键、条件替换均真实执行；故障在测试中替换Mongo insert/replace或SQL commit调用边界触发，不向生产类加入测试模式。

“重启”测试以BaseException中断在线流程、结束旧连接后创建新store/连接，未声称执行真实OS kill。SQL不可用测试使用真实TCP连接拒绝，持续阻止新业务SQL会话与恢复查询；锁池/数据库服务器仍运行，未声称关闭整个PostgreSQL容器。另有真实旧SQL事务持续持锁的测试，证明新文档锁不能替代事务结束核验。

| 验证 | 本轮实际输出 |
| --- | --- |
| 开始前pytest | 113 passed / 20未启用DB测试skipped |
| 用例TDD | 缺模块2收集错误→9通过；发布时间精度RED→新增第10项通过 |
| 双库TDD | 缺实现RED→16项故障/恢复通过；空正文兼容RED→新增第17项通过 |
| 完整pytest，两个DB开关均1，task4-all-010 | **160 passed / 0 skipped / 0 failed**；当前生产覆盖95.05% |
| 审查BIGINT回归，task4-bigint-red-011→green-012 | 原偏差7 failed/4 passed；修复后该11项及既有补偿用例12 passed，再增加等价锁回归 |
| 修复后完整pytest，task4-final-013 | **172 passed / 0 skipped / 0 failed**；当前生产覆盖95.12% |
| ruff check . | All checks passed；初轮未用import/排序已修正 |
| mypy src scripts migrations | 最终strict，56 source files通过 |
| check_file_limits.py | 最终54生产/脚本文件，最长133/300行 |
| ruff format --check . / uv lock --check --offline | 最终103文件格式通过 / 45依赖锁解析通过 |
| 交接文档复核 | 22个Markdown、94个本地链接、0失效/围栏错误；AGENTS30物理行 |

复现沿用[Task3命令](task-3-report.md)，使用新的项目内basetemp；创建恢复见test_create_recovery.py/test_create_fencing.py，BIGINT回归见test_bigint_compatibility.py。

单次独立只读审查发现1项Important（BIGINT解析集合不同），无Critical/Minor。reviewer自行执行10项用例测试、只读PG原生转换探针及staged diff；未运行会修改DB的完整回归。主执行者以失败测试复现7个偏差，再统一原生SQL转换，并补读路径/锁键；完整172回归及门禁通过。本次只有一轮修复，未安排二次审查，不冒称reviewer复核修复后代码。

审查未验收的边界由执行者保留：HTTP校验/错误和完整Unicode/超大ID差分在Task6；mutate/soft_delete、并发修改/删除及迟到CAS在Task5；恢复CLI/调度及长期批处理策略在Task5/7；OS kill/整个PG容器关闭未执行，不把模拟注入当作这些证据。最终README/status/计划/日志由本次交接同步，CI/部署与v1验收仍待Task6–7。

最终资源核对：临时SQL schema/Mongo集合0残留；两个专用测试容器已停止并确认Exited(0)，卷保留，参考前后端源码未改。文档链接/围栏与Git差异复核后以`feat(v1): add recoverable document creation and queries`保存本地提交，不合并main/推送。

## 未完成与下一步

Task5修改、软删除、并发变换与完整恢复CLI；Task6五接口及完整旧版差分；Task7CI/运行/E2E/版本验收。当前保持v1 implementing，不合并main或推送。

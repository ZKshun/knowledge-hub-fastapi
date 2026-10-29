# v1 Task 2：需求与实现对照

日期：2026-10-28；分支：`v1`；开始前 HEAD：`458f5528a3ce16020ab70661f2b84ceda0a19102`。本阶段实现、验证与独立审查完成；最终提交由 Git 查询。v1 尚未验收或合并 main。

## 完成哪些需求、如何完成

| 需求 | 实现方式与位置 | 验证与边界 |
| --- | --- | --- |
| 职责清晰、业务不绑定框架 | core 分配置/错误/ID/时钟；documents 分领域数据、命令、文本规则及应用存储端口。领域仅依赖标准库和轻量核心类型 | mypy strict 检查 src/scripts 27 文件；没有 Controller/Service 大文件或提前生成后续模块 |
| 保留旧文本算法 | `domain/text_metrics.py` 显式使用 ECMAScript 空白集合，计算 UTF-16 长度和截断，保留原汉字+剩余 token 计数 | 25 项文本测试及固定源码纯方法探测；含 BOM/NEL/中文标点/emoji/200 单元边界/半代理字符 |
| PATCH 不丢字段存在性 | `UpdateDocumentCommand` 复制为不可变 Mapping；保留显式 null 和相同 content；`DocumentMutation` 带 provided_fields | 16 项命令/领域测试；空 PATCH 与显式 null 可区分。实际 Mongo version 增长待 Task 5 |
| 给双库实现提供稳定接口 | frozen Document/Detail/Page、DocumentQuery、DocumentStatus；异步 `application/ports.py:DocumentStore` | 查询允许整数 status=999，但限制 page/page_size；领域不加入 HTTP/ORM/SDK；实际仓储待 Task 3–5 |
| 兼容旧环境配置且无导入 I/O | `core/config.py:Settings` 支持旧变量、范围校验与 SecretStr，默认不读 dotenv；`.env.example` 提前到本阶段交付 | 15 项配置测试：别名、显式 dotenv、无隐式加载、导入不实例化、凭据 repr/JSON/异常文本隐藏 |
| 字符串雪花 ID 可控且不静默重复 | `core/clock.py` 注入时钟，`core/ids.py` 使用 41/10/12 位、锁和明确异常 | 17 项测试：旧 worker7 向量、全部1024 worker、4096序列、并发、回拨/恢复、BIGINT上界、时区和非法输入 |
| 严格执行新 Python 文件上限 | `scripts/check_file_limits.py` 检查 src/scripts，300 物理行含空白/注释；读取失败或链接报错 | 10 项 CLI/门禁测试：300通过/301拒绝、无末尾换行、换行格式、大小写扩展、generated不豁免、坏UTF-8/缺目录；当前最长105行 |
| 跨会话继续并逐项汇报 | 同步 README、架构/规范/决策、规格/契约、计划、status、日志与本报告 | 下次从 Task 3 恢复；本报告是阶段对照，不替代 Task 7 的完整版本验收 |

## 后续必须沿用的接口

- `DocumentId` 定义在 `core/identifiers.py`，`IdGenerator.next_id()` 返回该字符串类型；`Clock.now()` 返回有时区 datetime。
- `Document` 包含完整 v1 元数据，id/title/created_at/updated_at 为必填；其余可空/默认值见 `domain/document.py`。content_id 允许草稿阶段为 None，不授权修改原 SQL 的 NOT NULL 列。
- `DocumentDetail(document=..., content=...)`；`DocumentPage(items=tuple[Document,...], total=..., page=..., page_size=...)`。不提前把 Mongo 版本塞入领域详情；持久层快照自行维护版本/操作标记。
- `CreateDocumentCommand` 不强制 API 校验，status/is_public 的 None 在 Task 4 按原版处理默认；标题/正文空字符串仍留给原 DTO 契约处理。
- `UpdateDocumentCommand.changes` 用内部 snake_case、只接受既定更新字段和标量；不得把 null 过滤掉。Task 6 负责原始请求校验和字段转换，Task 5 负责业务变换及存储动作。
- `DocumentStore.get/page/create/mutate/soft_delete` 均为 async；`mutate` 在同文档锁内读取再调用 transform，transform 返回 `DocumentMutation(target, provided_fields)`；存储器不能丢弃 provided_fields。

## 工程取舍和限制

1. 轻量 identifiers 单独存放，避免 core 的 ID 生成器反向依赖 documents；错误类型不携带 HTTP 状态，待 Task 6 映射原版错误。
2. JS 摘要可能保留未配对代理字符。Task 3 用 UTF-16 surrogatepass 编码/replace 解码等价方式做 BSON 的 U+FFFD 替换；不能使用 UTF-8 replace 产生 `?`。Task 6 同时验证 HTTP 字符串转义。
3. 纯 Node 探测确认旧库 worker0 与1生成同值、1023映射为0；新实现使用真实0–1023 worker位，保留正常位布局和字符串类型。时钟回拨或序列耗尽抛应用异常，不忙等、不重复；由调用层处理失败，未引入隐式重试。
4. 每活动进程使用唯一 worker，并在该进程共享生成器；相同 epoch 不随意变更。没有跨重启持久高水位或自动 worker 租约，不能宣称解决了部署时 worker 冲突/时钟回退重启问题。后续部署说明必须保留此约束。
5. `.env.example` 从原计划 Task 6 提前到 Task 2，便于配置交接；服务启动/客户端装配仍待后续。生产目录当前没有生成文件排除项，新增例外必须具体记录路径。

原算法依据为固定旧源码与本地运行探测；空白字符与设置实现还核对了 [ECMAScript 规范](https://tc39.es/ecma262/2026/)、[Pydantic Settings 官方说明](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)。

## 实际验证

环境：Python 3.12.14、现有锁定依赖；沿用专用 v1 checkout，没有启动 HTTP 或数据库。

| 验证 | 本轮结果 |
| --- | --- |
| 开始前完整测试 | 30 passed / 1 skipped；数据库探针未启用 |
| TDD 领域规则 | 缺少模块时2项收集错误 → 实现后41 passed |
| TDD 配置/ID | 缺少模块时2项收集错误 → 实现后32 passed |
| TDD 文件门禁 | 脚本缺失时10 failed → 实现后10 passed |
| `python -m ruff format .` / `python -m ruff format --check .` | 初次6文件格式化；最终只读检查60文件通过 |
| `python -m ruff check .` | All checks passed |
| `python -m mypy src scripts` | 27 source files，strict通过 |
| `python scripts/check_file_limits.py` | 27 Python files，最长105/300物理行 |
| `python -m pytest -q --basetemp=.local/pytest-runs/task2-all-009 --cov=knowledge_hub --cov-report=term-missing` | 113 passed / 1 skipped；生产语句+分支覆盖96.68%，现有85%门禁通过 |
| 文档/资源复核 | 20个Markdown、82本地链接、0失效或围栏错误；AGENTS30行；专用两容器均Exited(0)，参考工作区干净 |

覆盖率仅反映当前已实现模块，不证明未来 CRUD/恢复/HTTP 路径。未运行的数据库探针按既有环境开关跳过，不补记为通过；Task 1 的历史31通过记录保留。

独立 reviewer：单次只读审查 staged Task 2，**无 Critical/Important/Minor**；自行运行领域/配置/ID测试72通过、1项dotenv写文件测试为只读限制未选中，并核验格式/lint、文件门禁和 staged diff。完整113通过、覆盖率及mypy由主执行者实际运行；不将审查者未执行的检查归于审查者。最终交接复核检查 Markdown 链接/围栏、Git差异和参考工作区。

审查未验收的边界由执行者确认继续留在后续任务：HTTP校验/错误→Task6；BSON/迁移→Task3；跨库提交/补偿/恢复→Task4–5；并发写/防复活→Task5；worker部署与重启高水位→明确的部署约束；真实连接/生命周期/E2E/CI→Task3、6–7。遗漏这些验证会造成兼容或可靠性风险，故当前不验收完整v1。最终状态/日志/计划由本次交接同步。

## 未完成与下一步

Task 3：真实 PostgreSQL/Mongo 读取、迁移、BSON 映射、文档锁和操作日志；随后 Task 4–7 实现可恢复写入、HTTP 契约/E2E、CI 和完整 v1 验收。目前没有 FastAPI 五接口，没有新旧服务差分，没有 main 合并或推送。

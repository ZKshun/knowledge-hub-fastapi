# Python 代码质量规范

适用范围：新 FastAPI 项目的 Python 代码。旧 NestJS 代码只作为参考，不按本规范批量重构。

## 文件规模与职责

| 项目 | 规则 | 执行方式 |
| --- | --- | --- |
| 生产 Python 文件 | 硬上限 300 物理行，包含空行、注释和 docstring；目标 ≤200 | CI 检查 `src/**/*.py` 与手写 `scripts/**/*.py` |
| 路由文件 | 目标 ≤150 行；超过后按业务子资源或用例拆分，仍受 300 行硬上限 | 评审和行数报告 |
| 函数 | 目标 ≤50 物理行；超出应有清晰的单一算法理由 | 评审和静态报告 |
| 圈复杂度 | 每函数 ≤10 | Ruff C901，配置 max-complexity=10 |
| 测试文件 | 目标 ≤300 行，按场景拆分 | 评审；不混入生产覆盖率 |
| 生成文件和迁移 | `migrations/versions/*.py` 位于扫描根以外；工具生成文件只能按具体路径显式批准排除 | 当前无生产扫描路径豁免；不能把业务代码藏入这些位置 |

行数以 UTF-8 文本实际行计量，末行无换行仍算一行。禁止删空行、压缩多条语句、拼超长字符串或滥用动态执行来绕过上限。超过硬上限必须拆分职责，不能仅加 ignore。

已实现的 `scripts/check_file_limits.py` 扫描 `src`、`scripts` 的所有 `.py`（扩展名不区分大小写），含空行/注释，统一识别 LF/CRLF/CR；字符串中的 Unicode 行分隔符不额外计物理行。缺目录、读取/编码失败、符号链接和 Windows junction 均报错，不能静默漏扫。退出码：0 通过、1 超限、2 检查无法完成；不提供可随意调大的行数参数或泛化 generated 忽略。

## 命名与位置

- Python 包、模块文件、函数和变量使用 `snake_case`，如 `create_document.py`、`publish_document`。
- 类用 `PascalCase`，常量用 `UPPER_SNAKE_CASE`；布尔名用 `is_`、`has_`、`can_` 表达含义。
- 请求类如 `CreateDocumentRequest`、响应类如 `DocumentResponse`；持久化类如 `DocumentRow`、`DocumentContentRecord`；不混用三者。
- 单个用例与其业务模块放在一起；仓储以职责命名，如 `document_metadata_repository.py`，不建立无边界的 `manager.py`、`helper.py`、`utils.py`。
- 目录按 [架构](architecture.md)；新增抽象应解决当前版本真实重复，不为所有对象建立统一 BaseRepository/BaseService。

## 排版、类型与注释

- Python 3.12；UTF-8、LF、4 空格、文件末尾换行；Ruff format，行宽 100；字符串无法自动折行时仍须人工保证可读。
- Ruff lint 包含 E/F/I/UP/B/ASYNC/C901 等经过工具版本验证的规则；不将未经验证的规则名直接堆进配置。
- mypy strict；生产公开函数和边界有完整参数/返回类型；第三方缺失类型时在适配层缩窄 `Any`，不把 `Any` 扩散进业务层。
- 不写逐行解释代码含义的注释。仅说明业务原因、不变量、补偿顺序、兼容陷阱与外部协议要求。
- docstring 用于重要公开边界和不直观行为，不要求每个 getter 都写注释；禁止过时 TODO 无关联任务。
- 模块导入顺序自动管理；`__init__.py` 保持轻量，无隐式连接、全局业务实例或循环导入。

## API 与数据

- 外部 JSON 按原契约 camelCase；Python 属性 snake_case；Pydantic 的别名、null、缺失与类型转换策略必须有契约测试。
- ID 对外为字符串，禁止大整数被 JSON 数字化。内部采用明确的 ID 类型/别名和生成协议。
- 不直接返回 ORM 对象；通过响应模型和映射构建约定字段。不要自动包装为新的 `{code,data}` 结构。
- 时间在应用层使用明确时区，持久层通过适配保证原表 TIMESTAMP 与 API 日期语义兼容；不悄悄改已有列类型。
- 参数化 SQL/Cypher/ES 查询；配置在类型化 settings 层校验；测试不读取真实 `.env`。

## 错误、异步和可靠性

- 应用错误与 HTTP 错误分离。API 层适配原状态码与错误 body，不能默认接受 FastAPI 的 422 错误格式。
- 不使用无范围的 `except Exception: pass`。需要补偿或第三方降级时明确记录错误、恢复动作和是否影响用户结果。
- 超时、重试次数、退避、取消和并发限制显式配置。不可重试的校验错误不重试；幂等前提未满足不能盲目重放写操作。
- 同一 AsyncSession/Neo4j session 不跨并发任务共享；不把同步网络/CPU 密集操作放在事件循环里。
- 日志保留 request_id、task_id、document_id、版本等关联；密码、JWT、密钥、私有正文和完整记忆不进入普通日志或 tracing。
- 本地开发可使用合成模型适配器；正式启用模式缺少密钥时不能静默用哈希向量伪装正常语义检索。原版降级行为的契约差异必须显式记录。

## 测试和门禁

Task 2 后格式、lint、类型、文件门禁和现有测试命令均已实测；完整 v1 集成/E2E 仍未实现。下面是最终验收命令，不能把尚未存在的测试目录作为已通过证据：

```bash
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/check_file_limits.py
uv run pytest tests/unit tests/integration tests/contract tests/e2e --cov=knowledge_hub --cov-report=term-missing --cov-fail-under=85
```

覆盖率阈值计 `src/knowledge_hub`，排除范围仅允许生成代码，禁止把难测业务排除。v1 的纯文档/空工程阶段不运行一个必然失败的“零业务覆盖率”门禁来伪造完成；v1 交付时必须真正启用。

单元测试用确定性时钟、ID、模型和仓储；集成测试连隔离的真实 PostgreSQL/MongoDB 等依赖；契约测试与旧版同输入对比；E2E 验证业务闭环。变更缺陷先复现，再最小修复并验证；单纯文档调整只做链接、内容和 Git 检查，不强跑无关业务测试。

每次验证记录命令、环境、退出码和摘要。依赖未就绪、测试跳过或仅使用 mock 时必须标明边界；关键集成未通过时不能验收合并。

Ruff 格式化与检查依据：[官方文档](https://docs.astral.sh/ruff/formatter/)。具体工具版本和规则配置在 v1 验证后写入 `pyproject.toml` 与锁文件。

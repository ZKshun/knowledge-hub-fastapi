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

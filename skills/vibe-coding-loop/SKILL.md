---
name: vibe-coding-loop
description: >-
  Use for each coding task an AI agent will implement in a repo that already has
  (or is getting) agent docs: turn the request into a scoped task (goal,
  context, constraints, done-when), plan first if non-trivial, implement inside
  the architecture, verify with real commands, review against the spec, and feed
  repeated mistakes back into docs or checks. Also when documents are already in
  place and the next step is to code, or the user says 文档已经有了, 下一步写代码, 下一步是实现,
  开始编码, 开始实现, Vibe Coding, 做一个编码任务, 按任务让 AI 写代码, or 任务循环. When a
  bug's cause is still unknown, use debug-with-logs first, then come back here to
  commit and review the fix.
---
# Vibe Coding 任务循环

仓库里已经有（或正在写）给 AI 的文档时，每做一个编码任务就用本 skill。把请求收成有边界的任务，该计划的先计划，在既定架构里实现，用真实命令验证，对照规格审查，并把重复错误写回文档或检查。

还没有架构分流或文档体系时，先用 `architecture-from-idea` 和 `agent-constraint-docs`。硬规则要机器强制时用 `architecture-guardrails`。具体改仓库的操作交给 `code-changes`。

不要在一个对话里做整个项目。[OpenAI 最佳实践](https://learn.chatgpt.com/guides/best-practices)：一个聊天对应一个连贯的工作单元。

## 开始前先读什么

先读 `AGENTS.md` 的路由表，只打开当前任务类型指出的节。不要通读全部规格。若 `AGENTS.md` 不存在，停下来补文档，或明确这是原型并只遵守 README 里的几条禁止。

## 1. 写任务单

四要素（OpenAI 最佳实践），写法像 GitHub Issue：

- **Goal**：做成什么
- **Context**：相关文件、组件、要模仿的现有模块路径、「按模块 X 的方式实现」
- **Constraints**：不要做什么、不要扩大范围、架构禁令。任务碰到新边界（入口、适配器、外部调用）时，写明要加哪些日志（按 ARCH 日志节）
- **Done when**：可观察的验收，以及要跑的命令和预期退出码

有 UI 或交互时，说明「修好长什么样」。两种合理方案都说得通时，先由人选定。出处：[How OpenAI uses Codex](https://openai.com/business/guides-and-resources/how-openai-uses-codex/)；[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)。

做完判据：任务单可以交给一个没读过聊天记录的人（或新会话）接着做。

## 2. 非小任务先计划

小改动（单文件、行为清楚、不跨层）可以直接做。

否则：先让 AI 读相关文件、讲清现状，人纠正后再出计划。[Shipping Sora for Android with Codex](https://openai.com/index/shipping-sora-for-android-with-codex/)：先讲清数据怎么从 API 经 repository、view model 到 UI，再一起写迷你设计（改哪些文件、引入什么状态、逻辑怎么流），然后一步步执行。超长任务把计划存成文件，跨会话复用。

大任务先提交执行计划、审过再写代码。计划必须自包含。模板见 `agent-constraint-docs`。

做完判据：计划里能看出改哪些文件、不改哪些文件、如何验证。

## 3. 一次只做一个功能或一个切片

[长任务 harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的两个失败模式：想一次做完整个应用，留下半成品；后来的会话看到有进展就宣布完成。

对策：每次只做一个功能；结束时提交并写进度，保持可合入的干净状态。有功能清单时，只把完成项标为通过，不要改清单里的需求正文。

并行多个任务时用独立工作树，不要多人同时改同一文件。

## 4. 在架构里实现

- 新代码模仿已有的代表性功能，而不是另起一套分层。
- 业务规则放 core；UI 只经 seam 调用；新依赖边必须落在允许矩阵里。
- 强制不变量，不微管实现（harness）：在边界校验数据形状，但不为了风格琐事加规则。
- 人已经打好地基时，不要让 agent 在 UI 层塞进本该属于 core 的逻辑（Sora 文：模型缺深层架构判断时会这样做）。
- 新代码跨过边界时加日志：按 ARCH 日志节的字段和级别，带上请求 ID。错误带上下文记一次，不吞掉。core 只用注入的 logger。不记密钥和个人数据。加了新事件就更新 ARCH 事件表。

## 5. 用真实命令验证

给 AI 一条能返回通过 / 失败的检查。要求证据：跑了什么命令、输出是什么。不接受「全部通过」一句话。

能像真实用户一样做端到端检查时就做（例如浏览器），不要只跑单测就标完成（Anthropic 长任务 harness）。

同一提交的全量检查只跑一次；失败只重跑失败项，用来排除偶发失败。

证据可以引用日志行：贴出带请求 ID 的那几行（去掉密钥和个人数据）。新加了日志时，故意触发一次错误，确认能按请求 ID 找到它。日志本身也是代码，也会写错（addyosmani/agent-skills `observability-and-instrumentation`，MIT，借思路）。

**修 bug 时先读日志，再读代码。** 原因还不清楚时，先按 `debug-with-logs` 定位（复现 → 按请求 ID 读日志 → 根因假设 → 最小修复 → 回归测试），再回到这里提交和审查。日志定位不到问题时，先补上缺的那条日志，再修 bug。补的日志是修复的一部分，同一个 PR 提交，并写回 ARCH 事件表。OpenAI 的团队让 agent 直接查询日志、指标和链路，才能自己验证「启动在 800ms 内完成」这类要求（[Harness Engineering](https://openai.com/index/harness-engineering/)）。

做完判据：PR 或 `docs/evidence/` 里有命令、退出码，必要时有日志。

## 6. 独立审查

用没看过写作过程的新会话或子代理，对照 SPEC / PRD 审查：每条相关需求是否实现、列出的边界是否有测试，只报影响正确性的缺口，跳过纯粹风格争论（Claude Code 最佳实践）。格式和 lint 留给 CI。

OpenAI 建议用审查工作流，并且可以在离代码近的 `AGENTS.md` 里放代码审查规则。

## 7. 收尾

提交；更新进度文件；保持主干或功能分支可合入。验收结果只写 PASS / FAIL / 未核实。

提交前让 AI 用人话讲这次 diff：改了什么、为什么、可能影响什么；讲不清就不提交。再对照 `project-essentials` 总表「每个任务」那一列（存档点、错误提示、新密钥、新依赖）。

## 8. 把重复错误写回去

同一错误犯两次 → 复盘 → 更新 `AGENTS.md` 或对应规格。文档仍然管不住 → 打开 `architecture-guardrails`，升级为 lint、测试或 hook。

日志没能定位的缺陷，复盘里写「缺了哪条日志」，补进 ARCH 事件表。审查意见、重构、用户发现的缺陷，同样回写成文档或工具（harness：「文档不够时，把规则升级成代码」）。

可定期做小清理：扫偏离已写原则的代码，开小重构，而不是攒成大爆炸。

## 给无人值守任务的五问

来自 Claude Code 最佳实践，开始长时间跑之前必须能回答：

1. 知道「完成」长什么样吗？
2. 能自检吗？
3. 能碰什么？
4. 什么让它停（轮数、预算、范围）？
5. 结果去哪、谁签字？

## 交付前自检

- [ ] 任务有 Goal / Context / Constraints / Done when
- [ ] 非小任务有自包含计划
- [ ] 有命令与退出码，没有口头「全过」
- [ ] 没有一次做多个切片
- [ ] 重复错误已写回文档或检查
- [ ] 新边界有日志、带请求 ID；修 bug 时先读了日志，缺的日志已补上

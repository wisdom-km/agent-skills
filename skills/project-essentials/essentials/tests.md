# E6 冒烟测试 + 每个 bug 一条回归测试

强制：M-06 · 原型 SHOULD（建议一条冒烟检查，不做不停，但门禁表里要报告），曳光弹 MUST，长期 MUST（级别以 `project-essentials` 的 MANDATORY.md 为准）。不编造测试结果是红线 R-3。时机：开工；每修一个 bug。

类比：出门前摸一下口袋：钥匙、手机、钱包。不全面，但能挡住最常见的大错。

为什么：没有测试，AI 说「好了」你没法核对；同一个 bug 修好后还会回来。修 bug 时要先有一条失败的测试（obra/superpowers `systematic-debugging` 与 `test-driven-development`，MIT，借思路）；修完写一条测试防止复发（addyosmani/agent-skills `debugging-and-error-recovery`，MIT，借思路：Guard Against Recurrence）。

## 最低版

1. **一条冒烟测试**：启动应用 → 走一遍最主要的用户操作 → 没有报错。例如待办应用：新建一条待办 → 列表里能看到它。
2. 测试命令写进 README 和 `AGENTS.md` 命令表，一条命令就能跑。
3. 让 AI 交出命令和输出，不接受「测试都通过了」一句话。

## 每修一个 bug

- 写一条回归测试：**修之前跑会失败，修完跑会通过**。让 AI 把「修之前失败」的那次输出也给你看，否则这条测试可能根本测不到这个 bug。
- 测试名写清楚是哪个 bug，例如引用 issue 编号。
- 流程见 `debug-with-logs` 的 WORKFLOW.md 第 9 步。

## 曳光弹 + 长期

- 核心业务规则有单元测试，不依赖界面和网络。
- 少量端到端测试，像真实用户一样操作（Anthropic 长任务 harness 的建议：能像用户一样端到端检查时就做，不要只跑单测）。
- 新手不必追求覆盖率数字。先保证：主要操作有冒烟、修过的 bug 有回归。

## 检查

- 机器：CI 跑测试；修 bug 的 PR 没有改测试文件时给出警告（只警告，不硬拦）。
- 人：回归测试真的在修之前失败过。

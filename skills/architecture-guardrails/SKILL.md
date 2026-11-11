---
name: architecture-guardrails
description: >-
  Use when an architecture rule must hold without exceptions (dependency
  direction, UI must not import core internals, file size caps, no secrets,
  generated files untouched) and should be enforced by a linter, structural
  test, CI gate, or agent hook instead of prose. Also when rules are already
  written and the next step is machine enforcement, or the user says 下一步做门禁,
  下一步做机器检查, 把规则变成 CI, 把规则变成 lint, 架构护栏, 强制依赖方向, 不能有例外的规则, or to turn a rule into
  a hook.
---
# 架构护栏

当某条架构规则必须没有例外、应该由 linter、结构测试、CI 门禁或 agent hook 强制，而不是只写在文档里时，使用本 skill。典型对象：依赖方向、UI 不得引用 core 内部、文件大小上限、密钥不入库、生成文件不可手改。

先有规则正文（通常在 `ARCHITECTURE.md` / `RULES.md`），再做本 skill。文档怎么写见 `agent-constraint-docs`。编码任务循环见 `vibe-coding-loop`。

## 哪类规则必须进机器

把指令分成两类（[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)）：

- **非确定性**：提示、`AGENTS.md`、skill。模型会决定听不听。适合偏好和判断。
- **确定性**：hook、deny 规则、CI、lint、结构测试。环境每次都执行。适合不能有例外的不变量。

判断：如果你已经在文档里把某行加粗、复述、强调过，它还是被忽略，就把这行变成检查。反过来，只是风格偏好的 hook 应删掉。强制集合要小；规则多到变成爱好清单时，大多不该进门禁。

[Harness Engineering](https://openai.com/index/harness-engineering/)：强制不变量，不微管实现；文档不够时，把规则升级成代码。自定义检查的**报错信息要写成给 agent 的修复指令**，并指向规格位置。

没有检测违规的机制时，分层会在几年后被重新填满业务逻辑（Cockburn；以及「像推石头上山」的依赖规则执行问题）。

## 工作步骤

1. 从 ARCH / RULES 收集硬规则，列出表：编号 | 规则 | 现有怎么拦 | 缺口。
2. 每条缺口选一种最小强制手段（见下）。不要一上来上重型框架。
3. 把检查接到一条本地命令和 CI。命令写进 `AGENTS.md` 命令表。
4. 建立「门禁改法」说明：每个门禁 ID → 问题、怎么改、规格位置。检查失败时把这段输出给 agent。
5. 豁免只能走 ADR，并写到期日。过期后检查重新失败。
6. 用一个故意违规的最小样例，证明门禁真的会拒绝。样例不要留在主干，可放在会失败的分支或文档里的复现步骤。
7. 在禁止清单的「怎么拦」列填上门禁编号。未落地的必须写「未落地」，不能因「CI 全绿」被理解成已经在拦。

做完判据：故意违规会被对应命令以非 0 退出码拒绝；报错里有改法；`AGENTS.md` 能找到这条命令。

## 可选的强制手段（由轻到重）

按项目语言选择，不要把工具名写死成唯一方案。

- **依赖方向 / 分层**：模块边界 linter 或结构测试。例如 JS/TS 的 dependency-cruiser、Python 的 import-linter、Java 的 ArchUnit。规则写成「谁不能 import 谁」，与 ARCH 的依赖允许表一一对应。见 [recipes/dependency-boundaries.md](recipes/dependency-boundaries.md)。
- **文件或函数大小**：仓库内脚本，按扩展名设建议上限和硬上限。见 [recipes/file-size.md](recipes/file-size.md)。
- **密钥与危险路径**：gitignore、密钥扫描、agent 的 deny / PreToolUse（例如拒绝读 `.env`、拒绝改迁移目录）。
- **生成文件**：对生成目录做只读检查或格式化后的 diff 门禁。
- **格式**：PostToolUse 或 CI 里自动格式化，不要靠文档强调空格。
- **测试契约**：core 测试套件禁止引用 UI 或网络库；每个端口的内存实现与真实实现跑同一组契约测试。
- **文档新鲜度**：检查规格链接、状态行、目录路径是否还存在（doc gardening）。可选外部工具只作参考，引入前要审计。
- **agent 文档本身**：可选 linter 检查 `AGENTS.md` / skill 是否过期或自相矛盾；未审计前不要当必装项。

## Hook 与 CI

- Hook 适合「每次工具调用都要发生」的事（自动格式化、拦住读密钥）。CI 适合可重复的仓库不变量。
- 给 hook 的强制集合保持很小。
- 失败输出必须可执行：缺了哪个文件、应改成什么样、规格在哪一节。
- 同一提交的全量门禁只跑一次。

## 不要做的

- 不要用门禁规定用哪个无关紧要的库，或执行风格偏好。
- 不要照搬「门禁越少越好、agent 自己合入」。那是高吞吐团队的取舍，原文写明在低吞吐环境里不负责任。
- 不要在检查还没接入 CI 时，把规格写成「已经强制」。
- 不要为了过门禁而削弱规则原文；要改规则就走规格变更和 ADR。

## 交付前自检

- [ ] 每条硬规则要么有非 0 退出的检查，要么明确标 review
- [ ] 报错里有改法，并指向规格
- [ ] 至少做过一次故意违规被拒
- [ ] 豁免带到期日

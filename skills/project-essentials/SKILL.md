---
name: project-essentials
description: >-
  Use when a beginner or vibe coder starts a new project, picks up an existing
  one, or prepares to share or release it, and needs the basics every real
  project must have: version control and rollback, secrets and config,
  one-command run and README, tests, error handling, data backup and
  migrations, lockfiles, security basics, versions and CHANGELOG, health
  checks. Holds MANDATORY.md, the single list of mandatory items (MUST /
  SHOULD per tier: prototype, tracer bullet, long-lived), red lines, four
  gates, the gate table, and waiver rules. Also when the user asks what is
  mandatory, what the definition of done is, or wants to waive an item, or
  says 必备, 基础的东西, 新项目要准备什么, 上线前检查, 发布前检查, 密钥放哪, .env, 怎么回滚, AI 改坏了, 备份,
  数据丢了, 锁版本, lockfile, 安全检查, 版本号, CHANGELOG, 健康检查, 崩溃上报, 哪些是强制的,
  强制项, 门禁表, 完成定义, 这一条先不做, 豁免, essentials, checklist, before
  release, rollback, secrets, backup, mandatory, Definition of Done, waiver.
---
# 软件必备件

> **强制门禁**（本 skill 受 [MANDATORY.md](MANDATORY.md) 约束）
> 1. 开始前确认档位（原型 / 曳光弹 / 长期）和条件：[D] 存真实用户数据，[P] 别人能访问。档位不明先问；问不了按曳光弹。
> 2. 本 skill 的关口：G0 开工门、G3 发布门（G1、G2 由 `vibe-coding-loop` 触发）。到关口输出门禁表，每项只写 PASS（附证据）/ FAIL / WAIVED / N/A。
> 3. 任一 MUST 是 FAIL 就停下，报告「未满足：M-xx」和补法，不说「完成」。豁免只认用户原话，记进 `docs/WAIVERS.md`；红线 R-1 到 R-3 不可豁免。
> 4. 项目 `AGENTS.md` 还没有「强制项」一节时，在 G0 把本档 MUST 写进去（模板见 `agent-constraint-docs`），以后不加载本 skill 的会话也能读到。

开新项目、接手项目、准备给别人用或发布时使用本 skill。它列出真实软件都要有的基础件，按项目档位和时机告诉你现在该做哪些。

适用对象：编程基础不多、靠 AI 写代码的人。很多问题不是 AI 写错了代码，而是项目缺了一样基础件：没有存档点，改坏了回不去；密钥进了仓库；数据没备份。

**哪些是强制的，以 [MANDATORY.md](MANDATORY.md) 为准**：M-01 到 M-15 每项按档位标 MUST / SHOULD / —，加 3 条不可豁免的红线、4 个关口（G0 开工、G1 任务完成、G2 合入、G3 发布）、门禁表格式和豁免规则。其他 Skill 只引用它的编号。

档位（原型 / 曳光弹 / 长期）由 `architecture-from-idea` 第 2 步决定。档位不明先问；问不了按曳光弹。运行日志和定位 bug 不在本 skill：日志设计见 `architecture-from-idea` 第 4 步，出了 bug 用 `debug-with-logs`。规则要机器强制时用 `architecture-guardrails`。

## 总表

级别以 [MANDATORY.md](MANDATORY.md) 为准，这里是摘要。**MUST** = 不满足就停；**SHOULD** = 门禁表里报告，但不停；**—** = 不适用；**[D]** = 存了真实用户数据才适用；**[P]** = 别人能访问才适用。

| 编号 | 强制编号 | 必备件 | 原型 | 曳光弹 | 长期 | 什么时候做 | 细则 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E3 | M-01 | 版本控制与回滚 | MUST | MUST | MUST | 开工；每个任务 | [version-control.md](essentials/version-control.md) |
| E4 | M-03 | 密钥与配置（红线 R-1） | MUST | MUST | MUST | 开工；发布前 | [config-and-secrets.md](essentials/config-and-secrets.md) |
| E5 | M-02 | 一条命令跑、测、构建，README 能照着跑 | MUST | MUST | MUST | 开工；发布前 | [run-and-readme.md](essentials/run-and-readme.md) |
| E6 | M-06 | 冒烟测试 + 每个 bug 一条回归测试 | SHOULD | MUST | MUST | 开工；每修一个 bug | [tests.md](essentials/tests.md) |
| E7 | M-05 | 错误处理与用户看到的错误信息 | MUST | MUST | MUST | 开工；每个任务 | [errors.md](essentials/errors.md) |
| E8 | M-11 | 数据安全：备份、恢复、迁移、AI 不碰生产数据（红线 R-2） | [D] MUST | [D] MUST | [D] MUST | 开工；改数据结构时；发布前 | [data-safety.md](essentials/data-safety.md) |
| E9 | M-09 | 依赖锁定 | MUST | MUST | MUST（+ 审计） | 开工；加依赖时 | [dependencies.md](essentials/dependencies.md) |
| E10 | M-10 | 安全基础（新手版 8 条） | [P] MUST | [P] MUST | [P] MUST；ASVS L1 自查 SHOULD | 开工；发布前 | [security-basics.md](essentials/security-basics.md) |
| E11 | M-13 | 版本号、CHANGELOG、回滚办法 | — | SHOULD | MUST | 发布前 | [release.md](essentials/release.md) |
| E12 | M-14 | 健康检查与崩溃上报 | — | SHOULD | [P] MUST | 发布前 | [after-launch.md](essentials/after-launch.md) |

E1（能定位问题的日志，M-04）和 E2（定位 bug 的流程）在 `architecture-from-idea` 和 `debug-with-logs` 里，这里不重复。M-07 审查、M-08 CI、M-12 文档、M-15 无障碍没有单独的细则文件，级别见 MANDATORY.md。

## 怎么用

### G0 开工门（新项目或接手项目）

1. 问清两件事：存不存用户数据 [D]？会不会给别人用（别人能访问到）[P]？这决定 M-11、M-10、M-14 要不要做。
2. 确认档位。档位不明先问；问不了按曳光弹，并在门禁表里写明。
3. 按 MANDATORY.md，挑出本档「关口」列含 G0 的 MUST 和 SHOULD。
4. 每一项先做「最低版」（每个细则文件的第一节）。原型不要搭全套。
5. 把结果写进项目：`AGENTS.md` 写「强制项」一节（模板见 `agent-constraint-docs`）；命令写进命令表；禁止项写进 `RULES.md` 或 `AGENTS.md` 禁止摘要。
6. 输出 G0 门禁表（[templates/GATE_REPORT.md](templates/GATE_REPORT.md)）。任一 MUST 是 FAIL，不写业务代码。

### G1 / G2（每个任务、每次合入）

由编码循环（`vibe-coding-loop`）第 7 步触发：这次有没有新的存档点、错误有没有给用户人话和编号、有没有新密钥、有没有加依赖、测试和审查有没有证据。

### G3 发布门（给别人用之前、每次发布之前）

按 MANDATORY.md 挑出「关口」列含 G3 的项，逐项输出门禁表。只写 PASS（附证据）/ FAIL / WAIVED / N/A，不写「应该没问题」。任一 MUST 是 FAIL，不发布。

### 用户说「这一条先不做」

照抄原话，记进项目的 `docs/WAIVERS.md`（[templates/WAIVERS.md](templates/WAIVERS.md)）；长期项目另写一条 ADR。之后门禁表里这一条写 WAIVED 和编号。没有用户原话，不能写 WAIVED。红线 R-1 到 R-3 不能豁免：停下，说明风险，只做可逆的部分。

## 给 AI 的话

可以直接说：

> 这是一个新项目（原型 / 曳光弹 / 长期），会存用户数据，会给别人用。请按 project-essentials，列出现在必须做的必备件，每项先做最低版，做完给我看命令和结果。

> 准备发布了。请按 project-essentials 的 G3 发布门，输出门禁表，每项给出 PASS / FAIL / WAIVED / N/A 和证据。

## 什么时候停下问人

- 要碰生产数据、删数据、改数据库结构。
- 发现密钥已经进了仓库或推到了远端（先换密钥，再处理历史）。
- 要关掉某个检查、测试或安全设置。
- 想豁免一条 MUST（只有用户能决定；红线不能豁免）。
- 要给 agent 更大的权限（生产库、整台电脑、付费账号）。

## 交付前自检

- [ ] 问过「存不存用户数据」「会不会给别人用」，确认了档位
- [ ] 按 MANDATORY.md 选出的每个 MUST 都是 PASS（附证据）或 WAIVED（有用户原话）
- [ ] `AGENTS.md` 有「强制项」一节；新命令已写进命令表，并真的跑过
- [ ] 输出了对应关口（G0 或 G3）的门禁表；有 MUST 是 FAIL 时没有说「完成」或「可以发布」

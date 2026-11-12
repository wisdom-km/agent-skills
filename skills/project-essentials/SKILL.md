---
name: project-essentials
description: >-
  Use when a beginner or vibe coder starts a new project, picks up an existing
  one, or prepares to share or release it, and needs the software basics that
  every real project must have: version control and rollback, secrets and
  config, one-command run and README, smoke and regression tests, error
  handling and user-facing error messages, data backup and migrations,
  dependency lockfiles, beginner security basics, version numbers and
  CHANGELOG, health checks and crash reporting. Gives a checklist by project
  tier (prototype, tracer bullet, long-lived) and by moment (project start,
  every task, before release). Also when the user says 必备, 基础的东西, 新项目要准备什么,
  上线前检查, 发布前检查, 密钥放哪, .env, 怎么回滚, AI 改坏了, 备份, 数据丢了, 锁版本, lockfile,
  安全检查, 版本号, CHANGELOG, 健康检查, 崩溃上报, essentials, checklist, before
  release, rollback, secrets, backup.
---
# 软件必备件

开新项目、接手项目、准备给别人用或发布时使用本 skill。它列出真实软件都要有的基础件，按项目档位和时机告诉你现在该做哪些。

适用对象：编程基础不多、靠 AI 写代码的人。很多问题不是 AI 写错了代码，而是项目缺了一样基础件：没有存档点，改坏了回不去；密钥进了仓库；数据没备份。

档位（原型 / 曳光弹 / 长期）由 `architecture-from-idea` 第 2 步决定。运行日志和定位 bug 不在本 skill：日志设计见 `architecture-from-idea` 第 4 步，出了 bug 用 `debug-with-logs`。规则要机器强制时用 `architecture-guardrails`。

## 总表

档位：**必备** = 所有项目都要，包括明天就扔的原型；**曳光弹 + 长期** = 要留下来的代码才要；**条件** = 满足条件就必备；**可选** = 按项目判断。

| 编号 | 必备件 | 档位 | 什么时候做 | 细则 |
| --- | --- | --- | --- | --- |
| E3 | 版本控制与回滚 | 必备 | 开工；每个任务 | [version-control.md](essentials/version-control.md) |
| E4 | 密钥与配置 | 必备 | 开工；发布前 | [config-and-secrets.md](essentials/config-and-secrets.md) |
| E5 | 一条命令跑、测、构建，README 能照着跑 | 必备 | 开工；发布前 | [run-and-readme.md](essentials/run-and-readme.md) |
| E6 | 冒烟测试 + 每个 bug 一条回归测试 | 曳光弹 + 长期必备；原型建议有冒烟 | 开工；每修一个 bug | [tests.md](essentials/tests.md) |
| E7 | 错误处理与用户看到的错误信息 | 必备 | 开工；每个任务 | [errors.md](essentials/errors.md) |
| E8 | 数据安全：备份、恢复、迁移、AI 不碰生产数据 | 条件：存了用户数据 | 开工；改数据结构时；发布前 | [data-safety.md](essentials/data-safety.md) |
| E9 | 依赖锁定 | 锁文件必备；审计为长期 | 开工；加依赖时 | [dependencies.md](essentials/dependencies.md) |
| E10 | 安全基础（新手版 8 条） | 条件：别人能访问 | 开工；发布前 | [security-basics.md](essentials/security-basics.md) |
| E11 | 版本号与 CHANGELOG | 曳光弹 + 长期 | 发布前 | [release.md](essentials/release.md) |
| E12 | 健康检查与崩溃上报 | 可选：上线给别人用后建议 | 发布前 | [after-launch.md](essentials/after-launch.md) |

E1（能定位问题的日志）和 E2（定位 bug 的流程）在 `architecture-from-idea` 和 `debug-with-logs` 里，这里不重复。

## 怎么用

### 开工时（新项目或接手项目）

1. 问清两件事：存不存用户数据？会不会给别人用（别人能访问到）？这决定 E8、E10 要不要做。
2. 按项目档位，从总表挑出「开工」那一列要做的项。
3. 每一项只做「最低版」（每个细则文件的第一节）。原型不要搭全套。
4. 把结果写进项目：命令写进 `AGENTS.md` 命令表；禁止项写进 `RULES.md` 或 `AGENTS.md` 禁止摘要；没做的写「未做」和原因。

### 每个任务

编码循环（`vibe-coding-loop`）收尾时，对照总表「每个任务」那一列：这次有没有新的存档点、错误有没有给用户人话和编号、有没有新密钥、有没有加依赖。

### 发布前（给别人用之前）

按总表「发布前」那一列逐项过。全部写 PASS / FAIL / 未核实，不写「应该没问题」。

## 给 AI 的话

可以直接说：

> 这是一个新项目（原型 / 曳光弹 / 长期），会存用户数据，会给别人用。请按 project-essentials，列出现在必须做的必备件，每项先做最低版，做完给我看命令和结果。

> 准备发布了。请按 project-essentials 的「发布前」检查，逐项给出 PASS / FAIL / 未核实和证据。

## 什么时候停下问人

- 要碰生产数据、删数据、改数据库结构。
- 发现密钥已经进了仓库或推到了远端（先换密钥，再处理历史）。
- 要关掉某个检查、测试或安全设置。
- 要给 agent 更大的权限（生产库、整台电脑、付费账号）。

## 交付前自检

- [ ] 问过「存不存用户数据」「会不会给别人用」
- [ ] 按档位选出的每一项都做了最低版，或写了「未做」和原因
- [ ] 新命令已写进 `AGENTS.md` 命令表，并真的跑过
- [ ] 发布前检查每项都有 PASS / FAIL / 未核实

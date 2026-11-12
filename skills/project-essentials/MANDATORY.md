# 强制项与门禁（唯一真相源）

本文件是所有 Skill 共用的「必须项」清单。其他 Skill 只引用这里的编号（M-xx、R-x、G0–G3），不复制内容。

类比：飞机起飞前的检查单。不是凭记忆「应该都弄好了」，而是在固定的时刻逐项打勾；有一项没过，就不起飞。

正式定义：在固定关口（开工、任务完成、合入、发布）逐项核对的必须项清单。每项按项目档位标 MUST / SHOULD / —。agent 到关口必须输出门禁表；任一 MUST 不满足，就不能进入下一步，也不能说「完成」。

**诚实的限度：** 本文件和项目里的 `AGENTS.md` 都是给 AI 的文字指令，AI 可能不照做。Claude Code 文档原话：必须每次都发生的事，要做成 hook、deny 规则或托管设置；CLAUDE.md 是 guideline，Claude 可以判断它不适用（[best practices](https://code.claude.com/docs/en/best-practices)）。**真正拦得住的只有 CI、hook 和分支保护。** 所以强制分两层：文档层（本文件：让 agent 自己停下并报告）和机器层（命令失败就合不进去）。机器层的现成模板（`scripts/check`、pre-commit、CI、agent hook）在 `architecture-guardrails` 的 `templates/project/`，装法见它的 `recipes/mandatory-gates.md`。项目没装这些模板、或没接进 CI 和分支保护之前，本文件不等于「已经被机器强制」。

## 1. 符号

- **MUST**：不满足就停。不进入下一步、不说「完成」、不合入、不发布。唯一例外是第 6 节记录在案的豁免。
- **SHOULD**：门禁表里必须写出状态，但 FAIL 时可以继续。
- **—**：本档不适用。
- **[D]**：项目存了真实用户数据才适用（数据库、用户文件、本地存储里的内容）。
- **[P]**：别人能访问才适用（部署到网上、发布给别人装）。
- 条件满足时，即使是原型也按该行执行。

## 2. 档位

档位由 `architecture-from-idea` 第 2 步决定：

- **原型（Demo）**：只为回答一个问题，答完就扔。
- **曳光弹**：端到端最薄的一条真实路径，留下当骨架。
- **长期**：要演进、要上线、多人或多个 agent 会改。

**档位不明时：** 先用选择题问用户。问不了（例如无人值守任务），按**曳光弹**执行，并在门禁表第一行写「档位未确认，按曳光弹」。曳光弹比原型严、比长期轻。

## 3. 红线（不可豁免）

所有档位都适用。用户怎么说都不能豁免。

| 编号 | 红线 | 对应 |
| --- | --- | --- |
| R-1 | 密钥不提交进仓库（也不写进日志） | M-03 |
| R-2 | 不对真实用户数据做没有备份的不可逆操作（删除、覆盖、改结构） | M-11 |
| R-3 | 不编造测试结果或检查结果，包括门禁表里的证据 | M-06、所有 PASS |

用户坚持要越过红线时：停下，说明风险，只做可逆的部分。

## 4. 强制矩阵

| 编号 | 必须项 | 原型（Demo） | 曳光弹 | 长期 | 关口 |
| --- | --- | --- | --- | --- | --- |
| M-01 | 版本控制：git、小步提交 | MUST：git + 每个能跑的小步提交一次 | MUST：+ 功能分支 + PR | MUST：+ main 受保护，只经 PR 合入 | G0、G1、G2 |
| M-02 | 一条命令跑、一条命令测；README 写怎么跑 | MUST：一条命令能跑（有测试时一条命令能测）；README 第一行写「原型，会扔掉」和启动命令 | MUST：+ 新会话只照 README 能跑通 | MUST：+ CI 在干净环境跑通 | G0、G3 |
| M-03 | 密钥不进代码和仓库；`.env` 被忽略；有 `.env.example` | MUST（红线 R-1） | MUST：+ 提交前或 CI 做密钥扫描 | MUST：+ 远端开启 push protection | G0、G1、G2 |
| M-04 | 运行日志 | MUST 最小版：出错带上下文打印到一处；不打印密钥；`AGENTS.md` 写日志在哪看 | MUST：第一条端到端路径结构化 + request_id；故意出错演练一次 | MUST：ARCH 完整日志节 + 能机器查的日志规则进门禁 + 错误路径测试 | G0、G1 |
| M-05 | 错误处理 | MUST：不吞错（没有空 catch）；出错时用户能看到提示 | MUST：+ 提示是人话 + 错误编号；堆栈不给用户 | MUST：+ 全局兜底 + 出错默认拒绝 + 错误路径有测试 | G1 |
| M-06 | 自动测试 | SHOULD：一条能重复跑的冒烟检查（脚本也行）；已有测试却失败时按 MUST，挡住 | MUST：冒烟 + 每个 bug 一条回归测试 | MUST：core 单测 + 契约测试 + 回归 + 少量端到端 | G1、G2 |
| M-07 | 审查 | MUST：提交前 AI 用人话讲这次改了什么、为什么、可能影响什么；你能复述才提交 | MUST：新会话或子代理独立审查，对照规格 | MUST：独立 AI 审查；涉及密钥、数据、权限、门禁的改动要人审 | G1（原型）、G2 |
| M-08 | CI：每个 PR 自动构建和测试 | SHOULD | MUST | MUST：+ 分支保护把 CI 设为必需检查 | G2 |
| M-09 | 依赖锁定 | MUST：锁文件已提交 | MUST：+ CI 按锁文件安装 | MUST：+ 发布前依赖审计 + 自动安全更新 | G0、G2、G3 |
| M-10 | 安全基础 8 条（见 `essentials/security-basics.md`） | [P] MUST | [P] MUST | [P] MUST；OWASP ASVS L1 自查为 SHOULD | G0、G3 |
| M-11 | 数据安全：开发和正式数据分开、AI 不碰正式数据、删数据要人确认、备份 + 恢复演练、迁移文件 | [D] MUST：至少做到红线 R-2 | [D] MUST | [D] MUST：+ 迁移可回退 + CI 跑迁移 | G0、G3 |
| M-12 | 决定和架构文档 | SHOULD：`DECISIONS.md` 一行一个决定 | MUST：+ 依赖允许表 + 第一条路径的 ARCH 笔记 | MUST：ARCH / RULES / ADR 全套，与代码同一个 PR 更新 | G0、G2 |
| M-13 | 版本号、CHANGELOG、回滚办法 | — | SHOULD | MUST：语义化版本 + CHANGELOG + tag + 写明怎么退回上一版 | G3 |
| M-14 | 健康检查与错误上报 | — | SHOULD | [P] MUST：有服务端就有健康检查；客户端有错误上报，不带个人数据 | G3 |
| M-15 | 无障碍 / 多语言 | — | — | [P] SHOULD：有界面且面向公众时，过一遍 WCAG 基础项 | G3 |

没有 PR 的项目（多数原型直接提交到 main）：G2 的项在每次提交前随 G1 一起查。

### 证据：PASS 要看到什么

| 编号 | 证据 |
| --- | --- |
| M-01 | `git log --oneline` 里有本任务的提交号；长期：分支保护设置的截图或命令输出 |
| M-02 | README 里的命令在新终端照抄能跑，贴命令和退出码 |
| M-03 | `git ls-files` 里没有 `.env`；`.gitignore` 含 `.env`；有 `.env.example`；曳光弹起：密钥扫描的命令和退出码 |
| M-04 | 故意触发一次错误，贴出那条日志（原型：带上下文的错误输出；曳光弹起：按 request_id 找到的整条路径） |
| M-05 | 搜索结果显示没有空 catch；故意出错时用户看到的提示 |
| M-06 | 测试命令和退出码；回归测试在修之前失败的那次输出 |
| M-07 | AI 的人话说明（原型）；独立审查的结论（曳光弹起）；人审的批准记录（长期敏感改动） |
| M-08 | PR 上 CI 运行的链接和结果 |
| M-09 | 锁文件路径，且在 `git ls-files` 里；CI 的安装命令按锁文件安装；审计命令的输出 |
| M-10 | 8 条逐条写 PASS / FAIL / N/A；长期另附 ASVS L1 自查结果 |
| M-11 | 备份在哪；最近一次恢复演练的记录；迁移文件路径 |
| M-12 | `DECISIONS.md`、ARCH、ADR 的路径 |
| M-13 | tag、CHANGELOG 条目、回滚步骤 |
| M-14 | 健康检查的返回；一条错误上报样例（不含个人数据） |
| M-15 | WCAG 基础项逐项结果 |

「应该没问题」「测试都通过了」不是证据。证据是命令和退出码、提交号、文件路径、日志行或截图。

### 每档 MUST 速查

- **原型（7 项）**：M-01 git、M-02 一条命令跑 + README、M-03 密钥不进仓库、M-04 最小日志、M-05 不吞错、M-07 AI 用人话讲改动、M-09 锁文件。另加条件项：[D] 时 M-11，[P] 时 M-10。目的不是把原型做重：每项几分钟能做完，保证能回滚、能重跑、密钥不泄露、出错能看到原因。
- **曳光弹（10 项）**：M-01 到 M-09，加 M-12。条件项：[D] 时 M-11，[P] 时 M-10。
- **长期（11 项）**：M-01 到 M-09，加 M-12、M-13。条件项：[D] 时 M-11；[P] 时 M-10 和 M-14。

### 和必备件文件的对应

`essentials/` 里每个文件对应一个编号：E3 版本控制 = M-01；E5 一条命令跑 = M-02；E4 密钥 = M-03；E7 错误处理 = M-05；E6 测试 = M-06；E9 依赖 = M-09；E10 安全 = M-10；E8 数据安全 = M-11；E11 版本号 = M-13；E12 健康检查 = M-14。M-04 日志见 `architecture-from-idea` 第 4 步和 `debug-with-logs`；M-07 审查和 M-08 CI 见 `vibe-coding-loop`；M-12 文档见 `agent-constraint-docs`。

## 5. 四个关口

| 关口 | 什么时候 | 谁触发 | 不过会怎样 |
| --- | --- | --- | --- |
| G0 开工门 | 选定档位之后、写第一行业务代码之前；接手已有项目时 | `architecture-from-idea` 第 2 步末；`project-essentials`；`vibe-coding-loop` 发现项目没有强制项清单时 | 不写业务代码，先补齐 G0 的 MUST |
| G1 任务完成门 | 每个编码任务说「完成」之前；每次修完 bug | `vibe-coding-loop` 第 7 步；`debug-with-logs` 交付前 | 不说「完成」，报告「未满足：M-xx」 |
| G2 合入门 | 合入 main 之前 | `vibe-coding-loop` 第 7 步；CI；分支保护 | 不合入；CI 红就不合 |
| G3 发布门 | 第一次给别人用之前；每次发布之前 | `project-essentials`「发布前」 | 不发布 |

每个关口只查「关口」列里有它的编号。

## 6. 门禁表

agent 到关口时必须输出这张表。空白稿见 [templates/GATE_REPORT.md](templates/GATE_REPORT.md)。

```markdown
### 门禁 G1（任务完成）· 档位：曳光弹 · [D] 是 / [P] 否
| 编号 | 级别 | 状态 | 证据 |
| --- | --- | --- | --- |
| M-01 | MUST | PASS | 提交 a1b2c3d「保存待办：加超时处理」 |
| M-04 | MUST | FAIL | 新加的数据库调用没有带 request_id 的日志 |
| M-06 | MUST | PASS | `npm test` 退出码 0；新增回归测试 save-todo-timeout |
| M-08 | MUST | WAIVED | docs/WAIVERS.md W-002，2026-12-01 复查 |
结论：未满足（M-04）。下一步：补日志后重跑本表。
```

规则：
- 状态只有四种：**PASS / FAIL / WAIVED / N/A**。
- PASS 必须附证据（第 4 节）。没有证据就是 FAIL，或者写「未核实」并按 FAIL 处理。
- N/A 只用于本档是「—」，或条件 [D] / [P] 不成立的行，并写出理由。
- WAIVED 必须写豁免编号（W-xxx）。
- 任一 MUST 是 FAIL：结论写「未满足（M-xx）」。不说「完成」，不合入，不进入下一步。给出补法，并主动提出去做。
- SHOULD 是 FAIL：在结论里列出，可以继续。
- 门禁表贴在 PR 描述里，或存到 `docs/evidence/`。

## 7. 豁免

- 只有用户明确说出「这一条先不做」才算豁免。agent 不能自己判断「这次不需要」。
- 记进项目的 `docs/WAIVERS.md`：编号、时间、用户原话、豁免哪一条、理由、风险、何时复查（日期或条件，例如「转长期前」）。空白稿见 [templates/WAIVERS.md](templates/WAIVERS.md)。没记在这里的不算豁免。
- 长期项目：每条豁免另写一条 ADR，并在 WAIVERS.md 里链接它。
- 之后每张门禁表里，这一条显示 WAIVED 和豁免编号，不会悄悄消失。
- 到期或条件触发后，这一条恢复为 MUST。
- 红线 R-1 到 R-3 不能豁免。

## 8. 让门禁不依赖哪个 Skill 被加载

Skill 靠描述匹配加载。用户只说「开始编码」时，可能只加载一个 Skill；新会话里可能一个都没加载。所以要三层：

1. **每个 Skill 顶部有同一段「强制门禁」**，指向本文件。
2. **项目里持久化**（不依赖 Skill 是否加载）：
   - `AGENTS.md` 写「强制项」一节：档位、[D] / [P]、本档 MUST 编号、全量检查命令、豁免文件位置、「任一 MUST 不满足不得说完成」。模板见 `agent-constraint-docs` 的 `templates/AGENTS.md`。Codex 在做任何工作之前读取 AGENTS.md（[OpenAI 文档](https://developers.openai.com/codex/guides/agents-md)）。
   - `CLAUDE.md` 写一行 `@AGENTS.md`（Claude Code 支持 `@path` 导入）。
   - Cursor：`.cursor/rules/` 下放一条类型为 Always Apply 的规则，内容只指向 `AGENTS.md` 的强制项（[Cursor rules](https://cursor.com/docs/context/rules)）。
3. **机器层**（真正拦得住）：CI 必需检查、分支保护、pre-commit、agent hook。模板在 `architecture-guardrails` 的 `templates/project/`，见第 9 节。

## 9. 哪些能交给机器（模板已提供）

| 编号 | 机器怎么查 |
| --- | --- |
| M-01 | 分支保护：main 只经 PR 合入（[GitHub 文档](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)） |
| M-03 | 提交前或 CI 做密钥扫描；远端 push protection |
| M-04 | 日志规则 lint，见 `architecture-guardrails` 的 `recipes/logging.md`（已有） |
| M-06、M-08 | CI 跑测试；分支保护把 CI 设为必需检查 |
| M-09 | CI 按锁文件安装 |
| M-02 | README 里有启动 / 测试命令；原型和曳光弹的 README 第一行写明档位 |
| M-05 | 扫空 catch、`except: pass`、Go 空错误分支 |
| 其他 | 人查，或在门禁表里由独立审查确认 |

模板：`architecture-guardrails` 的 `templates/project/`。`scripts/check` 按 `scripts/check.conf` 里的档位算出每项是 MUST 还是 SHOULD，任一 MUST 失败就退出 1；能查的项、各档要求和故意违规验证见它的 `recipes/mandatory-gates.md`。退出码就是 G1 / G2 门禁表里这些项的证据；机器查不了的项，脚本输出 MANUAL 行提醒，照常在门禁表里附证据。

agent hook 的现状（都已核实官方文档）：Claude Code 的 Stop hook 用退出码 2 阻止 agent 结束，stderr 作为原因交回 agent；连续继续 8 次（中间没有调用工具）后不再阻止（[hooks](https://code.claude.com/docs/en/hooks)）。Cursor 的 `stop` hook 不能阻止结束，但可以返回 `followup_message`，作为下一条消息自动提交，默认最多 5 次（[Cursor hooks](https://cursor.com/docs/hooks)）。Codex 的 Stop hook 用退出码 2 或 `decision: "block"` 让 Codex 继续，项目里的 hook 要先在 `/hooks` 里信任（[Codex hooks](https://developers.openai.com/codex/hooks)）。这些 hook 都可能被关掉或绕过，所以硬门槛仍是 CI 必需检查加分支保护。

## 10. 来源

清单加关口、能机器查就机器查、例外要显式，是下面几家的共同做法（跨来源归纳，不是某一家的原话）。只借思路，不抄原文。

- Microsoft Engineering Fundamentals Checklist（默认分支锁定、密钥不进历史、每个 PR 自动构建测试、一条命令构建和测试）：https://microsoft.github.io/code-with-engineering-playbook/engineering-fundamentals-checklist/
- Microsoft Definition of Done（记录了足够的诊断 / 遥测才算完成）：https://microsoft.github.io/code-with-engineering-playbook/agile-development/team-agreements/definition-of-done/
- Microsoft SDL：https://www.microsoft.com/en-us/securityengineering/sdl/practices
- Software Engineering at Google 第 9 章（改动提交前审查）、第 11 章（Beyoncé Rule）、第 23 章（CI）：https://abseil.io/resources/swe-book/html/ch09.html 、https://abseil.io/resources/swe-book/html/ch11.html 、https://abseil.io/resources/swe-book/html/ch23.html
- Google SRE 发布检查清单：https://sre.google/sre-book/launch-checklist/
- OpenAI Harness engineering（用 lint 和结构测试机械地强制不变量；agent 互审）：https://openai.com/index/harness-engineering/
- Anthropic Claude Code best practices（hook 才是每次都执行；Stop hook）：https://code.claude.com/docs/en/best-practices
- DORA capabilities（版本控制、CI、测试自动化）：https://dora.dev/capabilities/
- NIST SSDF SP 800-218（PW.7 审查、PW.8 测试、PS.3 保留发布版本）：https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP ASVS（L1 是最低要求）：https://owasp.org/www-project-application-security-verification-standard/
- The Twelve-Factor App：https://12factor.net/

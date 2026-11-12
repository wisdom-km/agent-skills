---
name: agent-constraint-docs
description: >-
  Use when architecture is already agreed and the next step is to write or
  update documents that coding agents follow (AGENTS.md / CLAUDE.md, PRD,
  ARCHITECTURE, RULES or standards, exec plans, ADRs, acceptance records, PR and
  task templates); when creating them from an agreed architecture; or when
  existing agent docs are too long, stale, or contradictory. Also when the user
  says 架构已经定了, 下一步写文档, 下一步是写文档, 给 AI 的约束文档, 写项目文档, 把架构写成给 AI 的约束, or asks to
  generate AGENTS.md, CLAUDE.md, PRD, ARCHITECTURE, or RULES. Also when the
  logging or observability section of these docs is missing or thin, or the user
  says 日志写进文档, 可观测性怎么写, 日志规则.
---
# 给 AI 的约束文档

在架构已经（或正在）定下来、需要生成或更新 coding agent 会遵循的文档时使用：`AGENTS.md` / `CLAUDE.md`、PRD、ARCHITECTURE、RULES 或标准文档、执行计划、ADR、验收记录、PR 与任务模板。也用于现有 agent 文档太长、过期或互相矛盾时。

还没有分流（原型 / 曳光弹 / 长期）时，先用 `architecture-from-idea`。把「不能有例外」的规则变成 lint / CI / hook 时，再用 `architecture-guardrails`。每个编码任务的执行用 `vibe-coding-loop`。

详细空白模板在 [templates/](templates/) 目录，按需复制到项目里，不要把本 skill 全文贴进仓库。

## 总原则

1. 只写 AI 读代码读不出来、或每次都要花时间重新挖的东西。[Claude Code memory](https://code.claude.com/docs/en/memory)：「它读代码能找到、而且真的会去看，就别写。」
2. 每条规则要能被核对：用具体命令、路径、数字，不写「保持整洁」。
3. 一个事实只写一处，其他地方放链接。
4. 规则冲突时写明优先级。建议默认：用户当场的明确指示 > RULES > ARCHITECTURE > PRD > 历史草案。
5. 未核实的写「未核实」；数值没测就写「待定标」，不让 AI 自己填数。
6. `AGENTS.md` 是目录，不是百科。目标约 100 行，硬上限约 200 行。[Harness Engineering](https://openai.com/index/harness-engineering/)：「给一张地图，而不是 1000 页手册。」文件变大就拆到 `docs/` 并在这里引用。[OpenAI 最佳实践](https://learn.chatgpt.com/guides/best-practices)：短而准；发现重复错误后再加规则。
7. 架构图与分层规则写在 `ARCHITECTURE.md`，`AGENTS.md` 只指向它。不要在 `CLAUDE.md` / `AGENTS.md` 里抄目录结构和架构概述（Claude Code 最佳实践列为可以不再做的事）。

## 按项目类型取舍

- **原型**：`README.md`（第一行写会扔掉）+ 短 `AGENTS.md`（命令 + 3–5 条禁止）+ `DECISIONS.md` + `PROGRESS.md`。不要搭完整体系。`AGENTS.md` 写一行「日志在哪看」，禁止里有「不吞错、不打印密钥」。
- **曳光弹**：上面这些，加上一张依赖允许表，以及第一条端到端路径的简短 ARCH 笔记。笔记里写日志字段、请求 ID 在哪生成、怎么一路传。
- **长期**：生成本文列出的全套；长正文按节拆到 `docs/prd/`、`docs/arch/`，根文件只放索引。ARCH 写完整的日志节，RULES 写日志规则（L-xx），能查的接到门禁。

## 生成顺序

1. 从已确认的架构决定收集：一句话产品、范围外、依赖规则、禁止清单、命令、质量场景。
2. 先写 `ARCHITECTURE.md` 和 `PRD.md`（真相源），再写 `RULES.md`，最后写短 `AGENTS.md` 做路由。
3. 补模板：`docs/adr/`、`docs/exec-plans/`、`docs/acceptance/`、`docs/evidence/`、PR 与任务模板。需要正式批准时加 `docs/approvals.md` 和 `docs/spec-changelog.md`。
4. 每条硬规则在 RULES 或 ARCH 的「怎么拦」列写上门禁或标「review」。然后打开 `architecture-guardrails`。
5. 做完判据：新开一个干净会话，只读 `AGENTS.md` 就能找到要读的节，并且能按命令表跑通测试。

## AGENTS.md（或 CLAUDE.md）必须有的节

1. 一句话产品 + 不是什么。
2. 冲突优先级，并声明「本文只做指针」。
3. 开工前必读（通常是禁止清单和 DoD 的指针）。
4. **按任务类型读哪些节**（表格：任务类型 → 文件和节）。这是最有价值的路由表。不要要求 agent 先通读 PRD 和 ARCHITECTURE。
5. 命令表：安装、lint、类型检查、单测（含「只跑一个文件」）、全量检查、看日志（按请求 ID 查）；最好附上次实测退出码与日期，不把旧测量改写成新的。路由表里加一行「排查 bug → 先看日志，再读 ARCH 日志节」。
6. 禁止事项摘要，或指向 RULES 的清单。
7. 完成标准指针（DoD）。
8. 何时停下问人（规格冲突、范围变化、缺接口、花钱、密钥、改门禁）。
9. 可选：容易误导的地方（看着没用其实在用的目录、不许再抄的旧模式）。
10. 可选：子目录 `AGENTS.md` 只写本目录工具链，冲突以根为准。

加载机制备忘：Codex 从项目根往下合并每层 `AGENTS.md`，越近越优先，默认合计上限 32 KiB（[Agents.md 指南](https://developers.openai.com/codex/guides/agents-md)）。Claude Code 没有 `CLAUDE.md` 时读 `AGENTS.md`，或用 `@AGENTS.md` 导入后再追加专属内容（[memory](https://code.claude.com/docs/en/memory)）。聊天里的明确指示覆盖文档。

空白稿见 [templates/AGENTS.md](templates/AGENTS.md)。

## PRD（做什么）

1. 状态行 + 版本 + 同级文档指针 + 依据来源
2. 一句话
3. 为谁（用户与场景）
4. 范围：范围内 / **范围外（明确不做）**
5. 产品层核心原则（3–5 条，能当判断依据）
6. 用户故事（编号 US-xx，可按 P1/P2/P3）
7. 验收标准：确定性标准（AC-xx，必须能写成自动测试）与质量/性能标准（QM-xx，没基准前写「待定标」）分开
8. 边界情况
9. 有性能或质量目标时，写基准集或定标前提
10. 里程碑：每个写「交付 + 退出条件（可观察证据）」，不估时间
11. 决策记录或指向 ADR
12. 术语表
13. 假设

模板节借鉴了 github/spec-kit 的 `spec-template.md`（MIT）。空白稿见 [templates/PRD.md](templates/PRD.md)。

## ARCHITECTURE（怎么搭）

1. 设计目标，按优先级排
2. 进程 / 部署拓扑
3. 分层与依赖规则（图 + 文字；写明 UI → seam → core）
4. 调研依据（来源 → 要点 → 落到本项目的具体规定）——让 AI 理解「为什么」
5. 接口（seam）形状规则：只传普通数据、错误是数据、一个用户操作一次调用、大数据传 ID、不含展示信息、小而深
6. 目录结构 + 每个切片的统一模板
7. 模块清单；切片之间的依赖允许矩阵
8. 禁止事项表（编号 | 禁止什么 | 为什么 | 怎么拦）
9. 文件与函数大小（建议上限 / 硬上限 / 例外；豁免只走 ADR 且带到期）
10. 端口与引擎抽象、插件或注册表
11. 数据模型与存储、配置与密钥隔离、版本与迁移
12. 协议与版本协商（如有）
13. 运行日志与可观测性。目的：测试或线上出问题时，拿一个请求 ID 就能定位到哪一层、什么原因。要写：
    - 谁读日志、在哪读、看日志的命令（同步到 `AGENTS.md` 命令表）
    - core 怎么拿到 logger（端口或注入；core 不 import 具体日志库）
    - 格式（JSON 或 key=value）和每条必带的字段：时间、级别、事件名、请求 ID、模块、结果或错误、耗时
    - 级别含义：ERROR / WARN / INFO / DEBUG 各在什么时候用
    - 请求 ID 在哪生成、怎么跨 seam、端口和进程传递
    - 要记的事件表：事件 | 级别 | 字段 | 哪一层记 | 负责切片。至少覆盖请求进出、外部调用、错误、关键用户操作、启动停止
    - 绝不记什么：密码、token、session 值、连接串、密钥、个人敏感数据、整段请求体（[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)「Data to exclude」）
    - 日志去哪、留多久、谁能看
    - 排查时怎么读日志：先按请求 ID 过滤，再看第一条 ERROR 和它前面的外部调用
    - 规模变大后再加指标和链路追踪，写明「未落地」还是「已落地」

    按项目类型取舍：原型只在 `AGENTS.md` 写一行日志在哪；曳光弹写字段和请求 ID 怎么传；长期写全节。
14. 测试策略（core / 适配器契约 / 协议 / ui / e2e / 基准）
15. CI 门禁表（编号 | 工具 | 内容）。未落地的门禁要写明，避免「CI 全绿」被理解成全部已强制
16. 教训章（如果有旧系统）
17. 开发环境与命令
18. 质量属性场景 / 效用树
19. 决策记录与变更

空白稿见 [templates/ARCHITECTURE.md](templates/ARCHITECTURE.md)。

## RULES / 标准文档（怎么协作）

1. 适用对象（人和 AI）、冲突优先级
2. 编码约定（严格度、错误处理、禁止的逃逸注释等）；运行日志规则（L-xx：错误带上下文和请求 ID 记一次、不吞错、core 只用注入的 logger、新边界加日志、不记密钥和个人数据）
3. 测试命名与组织（建议「&lt;结果&gt; when &lt;条件&gt;」，带 AC 编号）
4. 依赖引入规则（用途、许可证、体积、替代方案；白名单 / 黑名单）
5. 分支、提交、PR：一次一件事或一个切片；Draft 是否优先按项目选择
6. 并行：开工前声明要改的切片与热点文件；契约先行；热点文件尽量小改
7. 测试纪律：同一提交全量只跑一次；失败只重跑失败项；flaky 隔离；skip 视为失败；付费或真机测试是否进门禁要写明
8. 评审清单
9. Agent 绝不能做的事（编号 | 禁止 | 机器兜底：门禁编号或 review）。典型：force push、直推主干、自己合入（若项目不允许）、发版、写入密钥、扩大范围、绕过门禁、手改生成文件、编造上游能力或测试结果
10. 文档规则（唯一真相源、改规格同 PR、变更记录、未核实标记）
11. 关键架构约束的执行细则 + 交接时必须原样引用的一句话 + 完成说明模板
12. Definition of Done：只列条件并指向已有条文，不另写一套

空白稿见 [templates/RULES.md](templates/RULES.md)。

## 执行计划

默认用轻型（适合有人审计划再写代码）：现状理解 / 计划-实际-证据表 / 决策记录 / 证据链接 / 自检「影响 ARCH 或 PRD 吗」。建议门槛：改动会跨模块，或预计超过一小块有边界的工作（[How OpenAI uses Codex](https://openai.com/business/guides-and-resources/how-openai-uses-codex/) 提到约一小时或几百行的粒度）。第一笔提交可以只有计划，审过再写实现。计划必须自包含，不依赖聊天记录。

长任务、可能跨多个上下文窗口时，改用 OpenAI 的重型 `PLANS.md`（页面标注 archived，结构仍可用）：Purpose / Progress / Surprises / Decision Log / Outcomes / Context / Plan of Work / Concrete Steps / Validation / Idempotence / Artifacts / Interfaces。要求：自包含、活文档、新手能端到端实现、产出可演示行为、术语用白话定义；验收写成可观察行为，不是内部属性。[cookbook 原文](https://cookbook.openai.com/articles/codex_exec_plans)。

两种骨架见 [templates/EXEC-PLAN.md](templates/EXEC-PLAN.md)。

## ADR 与其他记录

ADR 五节（Michael Nygard 2011）：背景 / 选项 / 决定 / 后果 / 状态（提议 / 采纳 / 被取代）。被取代时改状态并指向新页，不在旧文追加「后来改为」。SAP §22.7 可补：证据、谁做的、为什么走捷径。见 [templates/ADR.md](templates/ADR.md)。

- 任务单：关联 US/AC、切片、约束、涉及文件（标层与热点）、参照实现（要模仿的现有模块）、要做 / 不要做、验收命令与预期退出码。对应 OpenAI 的 Goal / Context / Constraints / Done when，以及「按模块 X 的方式实现」。
- PR 模板：改了什么为什么、计划或现状理解、测试证据（命令、结果、SHA）、新边界加了哪些日志、未验证项、自审表。
- 验收记录：结果只能是 PASS / FAIL / 未核实；可记密钥是否存在，不写值。
- 事故复盘：无指责；时间线、影响、检测、数据是否离开本机、修复、验证；哪条日志定位了问题，缺了哪条日志、补在哪。
- 批准记录（若需要）：时间 | 原话 | 批了什么 | 落点；没记在这里的不算批准。
- 门禁改法目录：每个门禁 ID → 问题、改法、规格位置；工具失败时把这段说明追加给 agent。

## 写完后的维护

- 同一错误犯两次：复盘并更新 `AGENTS.md`；文档管不住就升级为代码检查（OpenAI 最佳实践与 harness）。
- 定期检查文档是否过期（链接、状态行、目录是否还存在）。可选工具思路：文档 linter、漂移检查。
- Slack、文档站点、脑子里的决定，对 agent 等于不存在，要写进仓库（harness）。
- 强制不变量，不微管实现：例如要求在边界解析数据形状，但不规定必须用哪个库。

## 交付前自检

- [ ] AGENTS.md 明显短于真相源，且有「按任务类型读哪些节」表
- [ ] 每条硬规则都有「怎么拦」
- [ ] 没有把目录结构和架构长文抄进 AGENTS.md
- [ ] 命令表可复制执行；未测数字标了待定标
- [ ] ARCH 有日志节（原型至少在 `AGENTS.md` 有一行日志在哪），命令表里有看日志的命令

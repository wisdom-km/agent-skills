---
name: architecture-from-idea
description: >-
  Use when architecture is not decided yet and the user has a software idea or a
  new project, or wants to start the full flow from idea through architecture to
  coding: first choose throwaway demo vs tracer-bullet skeleton vs long-lived
  product, then pick the architecture (layers, dependency rule, ports/adapters,
  deep modules, UI-core split) and record the decisions before any code. Also
  when the user asks how to architect, layer, or modularize an app, or says
  还没定架构, 从想法开始, 怎么设计架构, 怎么分层, 怎么模块化, 先做 demo 还是长期项目, 原型还是正式项目, 从想法到架构, or
  走完全流程从想法到 Vibe Coding. Also when the user asks how to design
  runtime logging or observability into the architecture, or says 日志怎么设计,
  可观测性, 出了问题怎么定位.
---
# 从想法到架构

用户有软件想法或新项目、要决定怎么分层/模块化、或问「先做 demo 还是长期项目」时使用本 skill。先分流，再定架构，再写约束文档。未确认路径前不要写业务代码。

配套 skill（本步做完再打开，不要一上来全读）：
- 架构定稿后写给 AI 的文档：`agent-constraint-docs`
- 每个编码任务的循环：`vibe-coding-loop`
- 把「不能有例外」的规则变成机器检查：`architecture-guardrails`

需要向人解释术语时，再读同目录 [PRINCIPLES.md](PRINCIPLES.md)。demo 细则见 [DEMO.md](DEMO.md)，长期细则见 [LONG.md](LONG.md)。

编码实现、仓库改动交给 `code-changes`。中文表达用 `plain-chinese`。不要在本 skill 里写死模型名或推理档位。

## 第 1 步：把想法问清楚（不写代码）

用选择题问，直到能写出一页规格。至少问清：
- 谁用、解决什么痛、一句话产品
- 范围外是什么（明确不做）
- 最重要的 1–3 个质量（快、稳、安全、易改、省钱等）
- 预期寿命、几个人或几个 agent 会改
- 有没有必须对接的现成系统
- 出了问题怎么查：谁看日志（自己、测试的人、agent、运维）；在哪看（终端、文件、日志平台）；从发现问题到定位要多快

最后一问别省。项目没有日志，测试时出了错就只能猜。OWASP 也要求在需求和设计阶段就定下记什么（[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)「Which events to log」）。

出处：[OpenAI Codex 最佳实践](https://learn.chatgpt.com/guides/best-practices)（先访谈、挑战假设）；[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)（访谈到能写 SPEC，再开新会话按规格做）；《The Pragmatic Programmer》Tip 75–77。

做完判据：能用一句话说出产品、用户、范围外，并且用户确认了。

## 第 2 步：判断走哪条路

用下表判断。任一「长期信号」成立，就不要按纯 demo 做。

| 问题 | 原型（demo）信号 | 长期信号 |
| --- | --- | --- |
| 代码以后还用吗？ | 验证完就扔 | 要演进、要上线 |
| 寿命 | 几天到几周 | 数月以上 |
| 要回答的问题 | 一个具体问题（算法行不行、界面好不好用） | 整个系统怎么连、怎么长 |
| 多少人 / agent 并行 | 1 个 | 多个（[Harness Engineering](https://openai.com/index/harness-engineering/)：agent 一多，严格分层是早期前提） |
| 钱、隐私、安全、数据迁移 | 没有 | 有（《Software Architecture in Practice》§24.3：这些要从一开始设计进架构） |

三种结果，不要混：

1. **原型（prototype）**：只为回答问题，答完就扔。《Pragmatic Programmer》Topic 13：必须讲清楚这段代码是一次性的、不完整的、无法补完的。README 第一行写「原型，会扔掉」。
2. **曳光弹（tracer bullet）**：端到端最薄的一条真实路径，留下当骨架。Topic 12；SAP §1.3：先做骨架，通信路径打通，功能最少，再增量长大。
3. **长期项目**：走第 3–5 步完整设计。

出处还有：SAP §1.3「为高可改性精心设计的架构不适合一次性原型（反之亦然）」；Ousterhout《A Philosophy of Software Design》第 3 章 tactical vs strategic。作者提到策略式投入约 6–18 个月回本、持续把约 10–20% 时间投到设计上，这是作者个人判断，引用时注明。

做完判据：写下选了哪一种、一句理由，用户确认。

## 第 3 步：列出驱动因素

长期项目必做；曳光弹做简化版；纯原型可跳过，只写下「要回答的那个问题」。

- 主要功能写成用户故事，按 P1 / P2 / P3 排。
- 最重要的质量属性写成**质量属性场景**（六要素：来源、刺激、环境、对象、响应、响应度量），放进效用树，按「业务价值 H/M/L × 技术风险 H/M/L」排序。出处：SAP §3.3、§19.4。
- 写下约束（必须用的平台、许可证、预算）与关注点。出处：SAP §20.2。
- 把「可诊断」写成一个关注点，并写一条场景。例如：「测试时一次操作失败，开发者拿着报错里的请求 ID，在日志里找到出错的那一层和原因。」能定时间就写时间，定不了标「待定标」。监控要回答两个问题：坏了什么、为什么坏（[Google SRE Book 第 6 章](https://sre.google/sre-book/monitoring-distributed-systems/)）。系统要「埋点充分」：排查问题时不需要再临时加日志（[OpenTelemetry Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)）。

做完判据：每个排在前面的质量属性都有一条可测场景（有数字或可观察结果）。拿不到数字就标「待定标」，不编数字。

## 第 4 步：定架构

长期项目做完整 Iteration 0（SAP §24.3：中大型系统不能靠事后「涌现」补安全与性能）。曳光弹做最小版：依赖方向、核心与 UI 分开、一个装配入口、带请求 ID 的日志（下面第 8 条的简化版）。纯原型读 [DEMO.md](DEMO.md)，但下面第 1 条和第 2 条仍然要做。

按顺序做决定，每个关键决定写一行 ADR（背景 / 选项 / 决定 / 后果 / 状态）：

1. **领域核心是什么**：把业务规则列出来（校验、计价、状态转移、权限、失败条件）。它们以后只能住在 core。
2. **依赖规则**：源码依赖只能指向内圈；内圈不能提外圈的任何名字（函数、类、变量，以及外圈数据格式）。UI → 接口（seam）→ core。[Uncle Bob, 2012](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)。
3. **端口与适配器**：数据库、网络、模型服务、文件系统都放在端口后面；一个端口可插多个适配器（真实、内存假实现、测试夹具）。core 测试用假适配器跑。一个适配器只是假想接缝，两个适配器才是真接缝（mattpocock/skills `codebase-design`，MIT）。
4. **模块要深**：接口远比实现简单；按信息隐藏切模块，不按执行顺序切（时间分解是红旗）。《APOSD》第 4、5 章。
5. **按功能切片**：每片内部模板固定（domain / application(ports, use-cases) / adapters / ui / testing），对外只有一个入口。
6. **跨边界只传普通数据**：不传实体对象，不传数据库行；错误是数据（例如 Result）；一个用户操作一次调用。Uncle Bob：「simple data structures cross the boundaries」。
7. **唯一装配根**：只有一个地方 new 具体实现并注入；入口文件只装配，不写业务分支。
8. **运行日志与可观测性**：现在就定，不要等出了事再补。目标是：拿着一个请求 ID，就能找到出错的那一层和原因。逐项定下：
   - **日志也在端口后面**：core 只依赖一个很薄的 logger 接口，由装配根注入。core 不 import 具体日志库，也不用裸 `print` / `console.log`。具体日志库只在适配器和装配根里配置。
   - **结构化**：一条日志是一个事件。用 JSON 或 key=value，字段名全项目统一。至少有：时间、级别、事件名、请求 ID、模块、结果或错误、耗时。只是 JSON 还不算结构化，字段名和类型要固定（[OpenTelemetry Logs](https://opentelemetry.io/docs/concepts/signals/logs/)）。
   - **级别有定义**：ERROR 是操作失败；WARN 是没失败但不正常（重试、降级）；INFO 是发生了一件该记的事；DEBUG 是诊断细节，默认关（[OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) 的 SeverityNumber 表）。
   - **关联 ID**：入口生成请求 ID（或接收上游传来的 trace ID）。它跨 seam、端口、进程一路传下去，每条日志都带上（[OpenTelemetry Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)；OWASP 称为 interaction identifier）。
   - **在边界记**：请求进入和返回；每次适配器调用外部（数据库、网络、模型服务、文件）的结果和耗时；每个错误带上下文（哪个操作、相关 ID、原因）；启动、停止、配置变化。错误不吞掉。
   - **绝不记**：密码、token、API key、session 值、连接串、加密密钥、银行卡、个人敏感数据、整段请求体。这条和「密钥不进仓库、不进日志」是同一条规则（RULES N-01）。外部输入写进日志前去掉换行符，防日志注入（OWASP）。
   - **去哪、留多久**：进程把日志写到 stdout，由运行环境收集和存放；本地开发直接在终端看（[The Twelve-Factor App XI. Logs](https://12factor.net/logs)）。写下保留多久、谁能看。
   - 规模大了再加指标（metrics）和链路追踪（traces）。先用日志加请求 ID 打底。

   这条决定写一条 ADR。
9. **可插拔点**：预计会换的东西（服务商、引擎、存储、UI）在那里放端口或插件注册表。SAP §8.2 延迟绑定、§8.4 插件模式。
10. 用 ADD 迭代：每轮选一组驱动因素 → 选设计概念 → 实例化元素、分配职责、定接口 → 画草图并记决定 → 分析（最好找别人审）→ 风险驱动是否继续。SAP §20.2。
11. **Design it twice**：关键接口至少想两个方案再选。《APOSD》第 11 章。

Clean Architecture 的五个独立性（Uncle Bob）：独立于框架、可测（不靠 UI/DB/Web 测业务规则）、独立于 UI、独立于数据库、独立于任何外部机构。圈数不固定，依赖规则永远成立。

做完判据：有一张层或切片图、一张依赖允许表、一份禁止事项清单、每个关键决定一条 ADR，其中一条是日志决定（字段、级别、请求 ID 怎么传、绝不记什么、日志去哪）。

## 第 5 步：把架构写成给 AI 的约束

打开 `agent-constraint-docs`，生成：
- `AGENTS.md`（指针，约 100 行，不要写成百科）
- `PRD.md`、`ARCHITECTURE.md`、`RULES.md`
- 执行计划模板、ADR 目录、PR / 任务模板

把每条「不能有例外」的规则同时登记一个机器检查（打开 `architecture-guardrails`）。没有机器检查的标「review」。

人先手写第一个代表性功能（端到端），后面的功能让 AI「照着这个写」。出处：[Shipping Sora for Android with Codex](https://openai.com/index/shipping-sora-for-android-with-codex/)：人做架构、模块化、依赖注入、导航、鉴权和网络，再写几个代表性功能；「用同一套架构和模式做这个设置页」远好于无上下文。

做完判据：新开一个干净会话，只读 `AGENTS.md` 就能找到要读的节、能跑通测试命令。

## 第 6 步：进入编码循环

之后每个任务打开 `vibe-coding-loop`。不要在一个对话里做整个项目。

## 两条路各不能省什么

即使明天就扔的原型，也必须有：[DEMO.md](DEMO.md) 里的「绝不能省」清单（版本控制、一条命令能跑和测、密钥不进仓库、写明是原型、业务规则不写在 UI 里、决定至少写一行、结束时写回结论、出错时带上下文打印到一个能看到的地方）。

长期项目必须有：[LONG.md](LONG.md) 里的「绝不能省」清单（依赖方向由机器检查、core 测试不依赖 UI、入口只装配、不建 utils 垃圾桶、契约先行、门禁失败带改法、豁免走 ADR 且带到期、文档与代码同 PR、结构化日志加请求 ID 贯穿各层）。

## 来源与限度

原则来自 Uncle Bob 2012 博文，Ousterhout、Bass et al.、Thomas & Hunt 的书，以及上面列出的 OpenAI / Anthropic 页面。日志部分来自 Twelve-Factor、OWASP Logging Cheat Sheet、OpenTelemetry 文档和 Google SRE Book。[Harness Engineering](https://openai.com/index/harness-engineering/) 写明：他们让 agent 能直接查询日志、指标和链路，并用自定义 lint 静态强制结构化日志。文档骨架借鉴了按 Harness 思路管理的长期项目，以及 mattpocock/skills、obra/superpowers、github/spec-kit、addyosmani/agent-skills 的公开做法（均 MIT，只借思路）。

「严格按 OpenAI 标准」没有一份官方规范文件，还没核实这种说法。OpenAI 自己说明：端到端自治高度依赖那个仓库的结构和工具，不要假设能直接推广。合入策略不要照搬「门禁最少、agent 自己合入」——原文写明只适合极高吞吐，低吞吐环境里会不负责任。

## 交付前自检

- [ ] 用户确认了产品一句话、范围外、走哪条路
- [ ] 原型的 README 第一行写了「会扔掉」
- [ ] 有依赖允许表和禁止清单，长期项目的硬规则已标机器检查或 review
- [ ] 没有编造未测量的性能数字
- [ ] 写下了出问题怎么定位：日志决定有 ADR（原型至少满足 DEMO.md 的日志底线）

---
name: always-on-agents
description: >-
  Use when designing or building an always-on agent: an agent that wakes up on
  events (webhooks, user messages, background jobs) or on timers (follow-ups,
  daily or weekly schedules), works unattended across many runs, and reaches the
  user without being asked. Walks through deciding whether always-on is really
  needed, then designing five parts with templates: event inbox, timers,
  memory, permissions, and outbox, and ends with a verifiable checklist. Also
  when an existing chat agent should become proactive, or the user says
  常驻 agent, 一直在线的 agent, 主动提醒, 定时任务, 定时跑, 每天早上发我, 到点提醒,
  后台 agent, 被事件触发, webhook 触发 agent, 收件箱, 事件队列, 发件箱, 跟进提醒,
  agent 记忆, 跨会话记忆, 等我批准再做, always-on agent, proactive agent,
  background agent, event-driven agent, scheduled agent, cron agent.
---
# 常驻 agent：五个部件

> **强制门禁**（本 skill 受 `project-essentials` 的 MANDATORY.md 约束）
> 1. 开始前确认档位（原型 / 曳光弹 / 长期）和条件：[D] 存真实用户数据，[P] 别人能访问。档位不明先问；问不了按曳光弹。
> 2. 本 skill 的关口：G0 开工门（第 2 步定完五个部件之后、写业务代码之前）。到关口输出门禁表，每项只写 PASS（附证据）/ FAIL / WAIVED / N/A。
> 3. 任一 MUST 是 FAIL 就停下，报告「未满足：M-xx」和补法，不说「完成」。豁免只认用户原话，记进 `docs/WAIVERS.md`；红线 R-1 到 R-3 不可豁免。
> 4. 没装 `project-essentials` 时，按项目 `AGENTS.md` 的「强制项」执行；两者都没有，先建立 MUST 清单再继续。

要做一个「会自己醒来干活」的 agent 时使用本 skill：它被事件或定时器叫醒，在用户不在场时做事，再把结果告诉用户。本 skill 只管**架构设计**。不写业务代码。

**使用地图。** 开工时用平时读文件的方式看技能库 `skills/` 里每个 `SKILL.md` 的名字，对照本项目根目录的 `SKILL_MAP.md`。新名字标成未核实，不要编造关系和用过的记录。没有脚本，装上或打开旁边的网页也不会自动更新。一段工作结束时按 [`NAVIGATION.md`](../../NAVIGATION.md) 先改 `SKILL_MAP.md`，再改旁边的 `SKILL_MAP.html`；网页没写成就留着旧页并说明它过期。然后告诉用户：用过、正在用、下一步、卡住。项目根不清楚就不要写。

常驻 agent 其实不是一直开着。它大部分时间在睡觉。每次被叫醒做一段活，叫一次 **run**；做完把要记的事写下来，再睡。五个部件决定三件事：什么时候醒、醒来记得什么、结果怎么送到用户手里（[Anthropic: Building always-on agents](https://claude.com/resources/articles/building-always-on-agents)）。

配套文件（按需打开）：
- [PRINCIPLES.md](PRINCIPLES.md)：每个概念先讲日常类比，再讲正式定义。向人解释时读。
- [CHECKLIST.md](CHECKLIST.md)：五个部件的可验证检查项。设计完、上线前各过一遍。
- `templates/`：每个部件一份模板。
  - [inbox.sql](templates/inbox.sql)：事件收件箱表、worker 租约、取事件的写法
  - [timers.sql](templates/timers.sql)：定时器表、scheduler 一轮的写法
  - [MEMORY.md](templates/MEMORY.md)：记忆目录结构和每类文件的格式
  - [PERMISSIONS.md](templates/PERMISSIONS.md)：自动 / 先问 / 禁止 权限表、凭据代理、挂起的工具调用
  - [outbox.sql](templates/outbox.sql) 和 [SEND_POLICY.md](templates/SEND_POLICY.md)：发件箱表和发送策略

配套 skill：
- 还没定档位和整体架构：先用 `architecture-from-idea`。本 skill 是它的一个专题。
- 设计定了，写成给 AI 的文档：`agent-constraint-docs`（五个部件写进 ARCHITECTURE，选择写成 ADR）。
- 每个部件的实现：`vibe-coding-loop`，一个部件一个任务。
- 「同一事件只跑一次」「密钥不进 agent 环境」这类硬规则：`architecture-guardrails`。
- 跑起来出问题：`debug-with-logs`，按 `run_id` 和 `event_id` 查。

不要在本 skill 里写死模型名、推理档位或某家云服务。模板是 SQL 加 Markdown，换成哪种数据库、队列或语言都行。

## 第 0 步：先确认真的需要常驻

常驻 agent 比普通聊天 agent 多五个部件，也多一类风险：它拿着用户的权限，在没人看的时候做事。先用选择题问清楚：

| 问题 | 不需要常驻 | 需要常驻 |
| --- | --- | --- |
| 用户不发消息时，它要不要做事？ | 不要，只回答问题 | 要：到点做、收到外部事件就做 |
| 要做的事需要判断吗？ | 不需要：固定脚本加 cron 就够，不用模型 | 需要：要读内容、做决定、写人话 |
| 要跨几天记住进度吗？ | 不用 | 要 |
| 平台已经有现成的定时 / 提醒功能吗？ | 有，先用现成的 | 没有，或满足不了 |

左列全中，就不要做常驻 agent，告诉用户更简单的做法。拿不准时，按原型做一个最小版：一张收件箱表、一个 worker、一个直接发送的工具，先验证用户真的需要它主动说话。

做完判据：用户确认了「它在用户不在时要做的 1–3 件事」，以及每件事的触发方式（哪个事件、哪个定时器）。

## 第 1 步：确认档位和条件

- 档位按 `architecture-from-idea` 第 2 步判断。
- 常驻 agent 几乎总是 [D]：记忆里存着用户的指令、偏好和任务进度。按 [D] 处理，M-11 数据安全适用。
- 只要有 webhook 地址对外开放，或别人能给它发消息，就是 [P]，M-10 适用。
- 它会在无人值守时调用外部服务。红线 R-2（无备份不做不可逆操作）在这里最容易踩到，第 5 步的权限表必须覆盖。

## 第 2 步：设计五个部件

按下面顺序，每个部件用对应模板填一份，写进项目的 `docs/` 或 ARCHITECTURE 草稿。每个部件都回答「坏了会怎样」。

### 2.1 列出事件来源

先填一张表：来源（用户消息、哪个 webhook、哪个定时器、哪个后台任务）；来源自带的唯一 ID 是哪个字段；这个事件是**接着旧会话**（例如用户回复了 agent 的问题）还是**开新会话**。

规则：任何来源都不直接调用 agent，一律先写进收件箱。直接调用会出两种错：两个事件同时到，开出两个互相打架的 run；进程崩了，事件就丢了。

### 2.2 事件收件箱（模板 [inbox.sql](templates/inbox.sql)）

三样东西：一张持久的事件表、一个写表的入口（通常是 HTTP 接口）、一个读表的 worker（后台进程）。

- 入口只做轻量检查（webhook 签名、格式），写表后马上返回成功。慢了，webhook 提供方会当成失败重发。提示注入之类的深度检查放到 run 里做。
- 按「来源 + 来源事件 ID」去重：同一个 webhook 送两次，表里只有一行。
- 每个事件有状态：pending → running → done / failed。
- 收件箱是唯一真相源。worker 醒来先从表里取 pending；worker 中途死掉，新 worker 能取回同一个事件重试。重试有上限，超过就标 failed 并告警。
- 一个收件箱同时只有一个活着的 worker（用租约或锁）。先按「一个用户一个收件箱」起步。
- run 进行中又来了新事件：选一种并写下来——留给下一个 run、并进当前 run、或打断重来。
- worker 把连着到的几个 pending 合成一次 run。用户连发三条消息，agent 只回一次。

### 2.3 定时器（模板 [timers.sql](templates/timers.sql)）

- 两类：**跟进**（follow-up，agent 给自己定的一次性截止时间，例如「两天后看对方回了没有」）；**周期**（schedule，固定节奏，例如每天早报）。
- 定时器单独一张表，不放进收件箱。收件箱只放「现在就能处理」的事件。
- 定时器自己不启动 run。scheduler 按固定间隔扫表：到点的跟进标 done，到点的周期把下次时间往后挪，然后往收件箱写一个事件，再叫醒 worker。
- 自己写 scheduler，或用现成的 durable execution 引擎，二选一，写成 ADR。
- 周期任务要存时区。用户说「每天早上 8 点」，指的是用户所在时区的 8 点。

### 2.4 记忆（模板 [MEMORY.md](templates/MEMORY.md)）

- 只存**查不回来的东西**。别的系统里已经有的（工单、日历、文档），只存指针（链接或 ID）。
- 四类：用户指令（每次 run 都加载）；用户笔记（偏好、纠正过的错；多了拆小文件，只加载索引）；已经告诉过用户的话（防止重复说）；每个任务的进度文件（做了什么、还剩什么；只加载索引）。
- 记忆放在持久存储（数据库或对象存储），不放在 worker 本机磁盘。worker 换了，记忆还在。
- 每次 run 的固定开销（系统提示、工具定义、记忆索引）要小，并用模型服务的 prompt caching 降成本。
- 会话太长时，压缩旧消息或开新会话都会丢细节。要留下的东西，在 run 中途就写进记忆，不要指望会话还在。

### 2.5 权限（模板 [PERMISSIONS.md](templates/PERMISSIONS.md)）

- 每个工具调用只有三种处理：自动做、先问用户、禁止。把 agent 能调用的每个动作填进权限表。
- 密钥不进 agent 的运行环境，也不进提示词。agent 发不带密钥的请求，由环境外的**凭据代理**加上真密钥再转发。
- 风险高的动作先过一道自动审查（规则或分类器），拦下危险的，让 agent 换一种更安全的做法。最重要的决定一定留给用户。
- 需要用户批准时，用**挂起的工具调用**（deferred tool call）：这个 run 结束，会话停在这一步存起来；用户的答复作为新事件进收件箱，开一个 run 接着原会话跑。等答复期间，worker 照常处理别的事件。

### 2.6 发件箱（模板 [outbox.sql](templates/outbox.sql)、[SEND_POLICY.md](templates/SEND_POLICY.md)）

- 每个 run 只有三种结局：发一条消息；什么都不发；挂起一个工具调用请用户批准或补充信息。「什么都不发」是正常结局，不是失败。
- 大多数场景一个「发送」工具就够。要控制发送节奏、或要在发送失败时重试，才建正式的发件箱表加一个 dispatcher（发送进程）。
- 用户看到的是结果和几句要点，不是一步步的过程。
- 先少说话，再慢慢争取用户的注意力。发多发少用 eval 来调：准备一组「该发 / 不该发」的样例，每次改提示或策略都跑一遍。

### 2.7 日志

每个 run 记一行开始、一行结束：`run_id`、`inbox_id`、这次处理的 `event_id` 列表、新会话还是接旧会话、结局（sent / nothing / deferred / failed）、耗时。`run_id` 就是这个项目的 `request_id`（M-04），一路传到工具调用和发件箱。

做完判据：五份模板都填了；每个部件写了「坏了会怎样、怎么恢复」；用户确认了权限表里每一个「自动做」。

## 第 3 步：G0 门禁

按 `project-essentials` 的 MANDATORY.md 输出 G0 门禁表。和本 skill 最相关的几项：

- M-03：密钥只在凭据代理那一侧，agent 环境和提示词里没有。
- M-04：run 日志字段定了（第 2.7 节）。
- M-05：失败的事件标 failed 并告警，不静默丢掉。
- M-11（[D]）：记忆存储有备份和恢复步骤。
- M-10（[P]）：webhook 入口校验签名；事件内容当数据，不当指令。

任一 MUST 是 FAIL，不开始写业务代码。

## 第 4 步：交接

1. 用 `agent-constraint-docs`：把五个部件写进 ARCHITECTURE 的「常驻 agent」一节；每个二选一（自写 scheduler 还是用引擎、run 中来新事件怎么处理、要不要正式发件箱）写一条 ADR；把 [CHECKLIST.md](CHECKLIST.md) 里适用的项抄进验收标准。
2. 用 `vibe-coding-loop` 实现，一个部件一个任务。推荐顺序（先打通最细的一条真实路径）：收件箱 + worker + 直接发送 → 记忆 → 权限和挂起调用 → 定时器 → 正式发件箱（需要时才做）。
3. 「同一事件只跑一次」「同一收件箱只有一个 worker」「密钥不进 agent 环境」能写成测试或 CI 检查的，交给 `architecture-guardrails`。
4. 第一次给别人用之前（G3），按 [CHECKLIST.md](CHECKLIST.md) 全部过一遍，每项附证据。

## 来源与限度

- 五个部件、三种 run 结局、「先少说话」都来自 [Anthropic: Building always-on agents](https://claude.com/resources/articles/building-always-on-agents)（2026）。原文没有给 schema，本 skill 的表结构和检查项是我们自己写的，还没核实在大规模下的表现。
- 借鉴的公开做法（只借思路，没有复制代码或原文）：
  - [ax-llm/ax `ax-event-runtime`](https://github.com/ax-llm/ax/blob/main/src/ax/skills/ax-event-runtime.md)（Apache-2.0）：事件来源不直接调用程序；身份来自已认证的入口，不来自事件内容；先存结果再投递。
  - [hookdeck/webhook-skills `webhook-handler-patterns`](https://github.com/hookdeck/webhook-skills/tree/main/skills/webhook-handler-patterns)（MIT）：先验签，再解析，再幂等处理。
  - [vanja.io: Always-On AI Agents](https://vanja.io/always-on-agents/)（博客，未标许可证，只借思路）：定时器生成的事件用「定时器 ID + 到期时间」做去重 ID；worker 启动时把卡在 running 的事件放回 pending 并计数。
- 本 skill 只管设计。具体用哪家模型、哪家队列、哪个托管平台，由项目自己定，写进 ADR。

## 交付前自检

- [ ] 第 0 步问过「真的需要常驻吗」，用户确认了要它主动做的 1–3 件事
- [ ] 事件来源表写全了：来源、唯一 ID 字段、接旧会话还是开新会话
- [ ] 五份模板都填了，每个部件写了「坏了会怎样、怎么恢复」
- [ ] 权限表里每一个「自动做」都经用户确认；不可逆的动作不是「自动做」
- [ ] 密钥只在凭据代理一侧（M-03）
- [ ] 写明了 run 可以什么都不发，并有一组发送 eval 样例
- [ ] 输出了 G0 门禁表；有 MUST 是 FAIL 时没有开始写业务代码
- [ ] 若这一步实际用了本 skill：本项目 `SKILL_MAP.md` 有状态、证据和下一步理由。只打开文件不算用过

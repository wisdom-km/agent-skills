# 长期项目路径

只在第 2 步选了「长期项目」，或曳光弹要升级时读本文件。

## 目标

改一个功能只动一个地方；多人 / 多 agent 并行不冲突；可验证；可替换。

策略式投入：持续把一部分时间花在设计上。《APOSD》§3.3 作者建议约 10–20%，回本期约 6–18 个月，这是作者个人判断。

## 架构与目录

完整做主 skill 第 4 步：分层 + 依赖规则 + 端口适配器 + 功能切片 + 装配根；硬规则用机器强制。

推荐目录（通用骨架，按语言替换扩展名）：

```
AGENTS.md                 指针（≤100 行）：一句话产品、冲突优先级、按任务类型读哪些节、命令表
PRD.md                    做什么（可拆到 docs/prd/，这里放索引）
ARCHITECTURE.md           怎么搭（可拆到 docs/arch/）
RULES.md                  怎么协作：约定、PR、禁止清单、DoD
DESIGN.md                 有 UI 才要
docs/
  exec-plans/             执行计划（文件名 = 分支名；或按 OpenAI 分成 active/completed）
  adr/
  acceptance/
  evidence/<PR号>/
  approvals.md            没记在这里的不算批准（若项目需要正式批准）
  spec-changelog.md
  references/             第三方库说明、llms.txt 等（可选）
  incidents/TEMPLATE.md
packages/ 或 src/
  contracts/              跨边界的类型、协议（契约先行）
  kernel/                 极小共享原语（Result、ID、Logger 接口、请求 ID…）
  features/<slice>/       每个切片同一模板：
    README.md             职责、公开 API、所有者、热点文件
    src/index.*           用例 seam（唯一入口）
    src/pure.*            展示用纯函数
    src/domain/           纯规则，一个概念一个文件
    src/application/ports/
    src/application/use-cases/
    src/adapters/
    src/ui/
    src/testing/          对外的 fake 与契约测试
    test/core/ test/adapters/ test/ui/
apps/<app>/…/composition-root.*   唯一装配根（也在这里配置具体日志库并注入）
tools/                    依赖方向、文件大小、文档链接、门禁改法目录
.github/                  PR 模板、任务模板、CI
```

测试：core 只经 seam，不渲染 UI、不联网；core 测试用内存 logger 假实现，可以断言关键错误会产生一条带请求 ID 的日志；每个端口一份共享契约测试，内存实现和真实实现都跑；少量 e2e；重要不变量可加属性测试（《Pragmatic Programmer》Tip 71）。

依赖偏好「无聊」、稳定、能在仓库里完全理解的技术（[Harness Engineering](https://openai.com/index/harness-engineering/)）；先定许可证白名单。

## 绝不能省

1. 依赖方向由机器检查，不靠自觉。没有检测机制，几年后又会在 UI 里塞满业务逻辑（Cockburn；Seemann「像推石头上山」）。OpenAI harness：自定义 linter + 结构测试。
2. core 测试不依赖 UI，能在无界面环境跑完。
3. 入口 / 装配文件只装配，不写业务分支。
4. 不写模块级可变状态；不建 `utils` / `helpers` 垃圾桶目录（《Pragmatic Programmer》Tip 47）。
5. 契约先行：接口类型单独先合入，再并行实现。
6. 门禁失败的输出带「怎么改」（写成给 agent 的修复指令）。
7. 豁免只能走 ADR，并带到期时间。
8. 文档与代码同一 PR 同步；要有机制查文档过期。
9. 运行日志按 ARCH 的日志节设计并执行：结构化；请求 ID 贯穿各层；每个边界有日志；错误带上下文、不吞掉；不记密钥和个人数据；写明日志去哪、留多久。能机器检查的进门禁（`architecture-guardrails` 的 `recipes/logging.md`）。OpenAI harness 用自定义 lint 静态强制结构化日志，并让 agent 能直接查日志、指标和链路（[Harness Engineering](https://openai.com/index/harness-engineering/)）。

文档写完后，打开 `agent-constraint-docs` 和 `architecture-guardrails`。

## 不要照搬的流程

- 多角色「Draft → 审查 → 业主合入」适合多 bot、低吞吐的长期项目；单人项目会被压垮，做成可选。
- OpenAI 内部「门禁最少、短 PR、agent 可自己合入」只适合极高吞吐，原文写明在低吞吐环境里会不负责任。

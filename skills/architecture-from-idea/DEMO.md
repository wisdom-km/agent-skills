# Demo / 曳光弹路径

只在第 2 步选了「原型」或「曳光弹」时读本文件。

## 目标

- 原型：最快回答一个问题。代码验证完就扔。
- 曳光弹：打通一条端到端真实路径，留下当骨架。

战术式编程可以接受，但要知道在借债。《APOSD》§3.1–3.3：你还的会比借的多；代码一旦成了意大利面就几乎修不好。

## 最小架构

单仓单进程即可，但下面这件事成本很低、是以后升级的种子：

**业务规则写成纯函数，不写在 UI 事件处理器里，也不直接做 IO。**

依赖选「什么快用什么」。文档只要能跑起来，不要搭完整 PRD/ARCH 体系。

## 最小目录

```
my-demo/
  README.md          第一行：原型或曳光弹；用途；会不会扔；一条启动命令
  AGENTS.md          ≤30 行：怎么跑、怎么测、3–5 条禁止
  DECISIONS.md       每行：日期 | 决定 | 理由
  PROGRESS.md        做到哪了、下一步
  src/
    core/            纯函数：业务规则（不 import UI、不做 IO）
    app.*            入口 + IO + UI，调用 core
  tests/
    smoke.test.*     一条端到端或核心规则测试
  .gitignore         含 .env
```

## 最小日志

原型不必搭日志系统，但出错时要能看出错在哪：

- 出错时打印出来，带上下文：哪个操作、相关 ID 或输入、错误原因。只打一句「失败了」不够。
- 所有输出去一个地方：终端，或一个日志文件。`AGENTS.md` 写一行「日志在哪看」。
- 不吞错：不写空 catch。
- 不打印密钥和个人数据。
- 好坏日志对比、出错后怎么按日志查：见 `debug-with-logs`。

曳光弹多做一步：第一条端到端路径就打日志。入口生成一个请求 ID，UI、seam、core、适配器每一层的日志都带上它。用一个结构化日志写法（JSON 或 key=value），以后不用重写。做完故意让这条路径出一次错，再拿请求 ID 在日志里找到整条路径。出处：addyosmani/agent-skills `observability-and-instrumentation`（MIT，借思路）：完成前先触发错误，按 requestId 在日志里找到它；[The Twelve-Factor App XI. Logs](https://12factor.net/logs)：进程只写 stdout。

原型可以不写测试（mattpocock/skills `prototype`：目的是尽快学到东西）。曳光弹至少留 1 条冒烟，再加几条核心规则单测。决策用一个 `DECISIONS.md` 列表即可，不必上完整 ADR 流程。

## 绝不能省（即使明天就扔）

1. 版本控制，频繁提交（《Pragmatic Programmer》Tip 28；Anthropic 长任务 harness 用 git 回退坏改动）。
2. 一条命令能跑起来，一条命令能测。[OpenAI 常见错误](https://learn.chatgpt.com/guides/best-practices)：不告诉 agent 怎么构建和测试。
3. 密钥不进仓库、不进日志。
4. 写明「这是原型」，避免被人当成能上线的代码（Topic 13）。
5. 业务规则和 UI / IO 分开放。
6. 决定写下来，哪怕一行（SAP §22.7）。
7. 原型结束时把结论写回：哪个问题、答案是什么、证据（mattpocock `prototype`：Capture it when done）。
8. 出错时带上下文打印到一个能看到的地方，不吞错（见上面「最小日志」）。

## 退出

- 原型：答案写进决定，代码扔掉或放到单独分支，不要默默留在主干。
- 曳光弹：转长期之前，补一次 Iteration 0（第 3–5 步），包括第 4 步的日志决定，再补机器检查。

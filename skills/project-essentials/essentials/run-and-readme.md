# E5 一条命令跑、测、构建，README 能照着跑

档位：必备。时机：开工；发布前。

类比：菜谱。别人照着菜谱能做出同一道菜，才算写对了。

为什么：OpenAI 列出的新手常见错误之一，是不告诉 agent 怎么构建和测试，让它看不到自己的工作（[Codex best practices: Common mistakes](https://learn.chatgpt.com/guides/best-practices)）。Twelve-Factor 要求完整、明确地声明全部依赖，不依赖系统里碰巧装了的东西（[II. Dependencies](https://12factor.net/dependencies)）。

## 最低版

README 开头固定写这几行：

```markdown
## 怎么跑
- 安装：`<一条命令>`
- 启动：`<一条命令>`
- 测试：`<一条命令>`
- 日志在哪看：`<位置或命令>`
- 需要的配置：见 `.env.example`
```

同样的命令写进 `AGENTS.md` 命令表，并写上「上次实测」的日期和退出码。

## 怎么验证

新开一个干净目录，重新克隆仓库，**只照 README 做**，能跑起来、测试能过，才算写对。可以让一个没看过这个项目的新会话 agent 来做，它卡在哪，README 就缺哪。

## 曳光弹 + 长期

- CI 在干净环境里跑一遍安装、测试、构建。
- 写明需要的运行时版本（Node、Python 等），最好放进项目文件（例如 `.nvmrc`、`.python-version`）。
- 开发环境和正式环境尽量一样（[The Twelve-Factor App X. Dev/prod parity](https://12factor.net/dev-prod-parity)）。

## 检查

- 机器：CI 干净安装 + 测试。
- 人：新会话照 README 跑通了；命令表的「上次实测」不是空的。

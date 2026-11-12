# E3 版本控制与回滚

档位：必备。时机：开工；每个任务。

类比：游戏存档。每过一关存一次；打坏了就读档，不用从头玩。

为什么：AI 一次能改很多文件。没有存档点，改坏了就回不去。Anthropic 让长任务 agent「用描述清楚的提交信息把进度提交到 git」，这样能「用 git 回退坏的改动、恢复可工作的状态」（[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)）。小改动审得更快、更彻底，也更容易回滚（[Google eng-practices: Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)）。

## 最低版

1. 项目第一天就 `git init`，并推到一个私有或公开的远端仓库。
2. 每完成一个能跑的小步，就提交一次。让 AI 动手前，先确认 `git status` 是干净的。
3. 提交前看 diff，并让 AI 用人话讲：这次改了什么、为什么、可能影响什么。讲不清就不提交。Simon Willison 的规则是：自己讲不清这段代码做了什么，就不提交（[Not all AI-assisted programming is vibe coding](https://simonwillison.net/2025/Mar/19/vibe-coding/)）。
4. `.gitignore` 里先放 `.env`、构建产物、依赖目录。

## 改坏了怎么办

| 情况 | 做法 |
| --- | --- |
| 还没提交 | 让 AI 列出改了哪些文件，丢弃这些改动，回到上一个提交 |
| 已经提交，知道是哪一次 | `git revert <提交>`：生成一个反向提交，历史不丢（[git revert](https://git-scm.com/docs/git-revert)） |
| 已经提交，不知道是哪一次 | `git bisect`：二分查找引入 bug 的提交（[git bisect](https://git-scm.com/docs/git-bisect)） |
| 已经推到远端、别人也拉了 | 用 `git revert`，不要改写已推送的历史 |

不要让 AI 在你不知情时执行 `git reset --hard`、`git push --force`。这两个会丢东西，执行前要你确认。

## 曳光弹 + 长期

- 一个功能一个分支，`main` 保持能跑。
- 打开分支保护：合入前必须走 PR、必须通过检查（[GitHub: About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)）。
- 并行多个 agent 时用独立工作树（worktree），不要同时改同一批文件。

## 检查

- 机器：分支保护（禁止直推 main）；提交前钩子跑密钥扫描（见 [config-and-secrets.md](config-and-secrets.md)）。
- 人：PR 或提交说明里能讲清改了什么；每个任务结束时工作区干净。

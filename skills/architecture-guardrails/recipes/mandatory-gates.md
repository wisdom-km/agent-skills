# 强制门禁模板：scripts/check、pre-commit、CI、分支保护、agent hook

类比：MANDATORY.md 是检查单，这里是闸机。检查单靠人自觉打勾；闸机不刷卡就不开门。

正式定义：把 MANDATORY.md 里能机器查的 MUST 项，做成一条命令 `scripts/check`。再把这条命令接到四个地方：提交前（pre-commit）、agent 结束前（Stop hook）、每个 PR（CI）、合入 main 前（分支保护的必需检查）。命令退出码非 0，就不能说「完成」，也合不进去。

模板在 [../templates/project/](../templates/project/)，按项目里的路径摆好，整个目录复制进项目根目录即可。编号（M-xx、R-x、G0–G3）以 `project-essentials` 的 MANDATORY.md 为准。

## 1. 文件清单

| 模板文件（复制到项目同一路径） | 作用 | 哪一档必须有 |
| --- | --- | --- |
| `scripts/check` | 一条命令跑全部机器检查；任一 MUST 失败退出 1 | 所有档：MUST（G1 证据就是它的退出码） |
| `scripts/check.ps1` | 同上，给 Windows PowerShell 用；检查项和输出相同 | Windows 上用 |
| `scripts/check.conf` | 档位、[D] / [P]、启动 / 测试 / 安装命令。纯文本，不会被执行 | 和 `scripts/check` 一起 |
| `.pre-commit-config.yaml` | 提交前跑 gitleaks、几个通用检查、`scripts/check --fast` | 原型 SHOULD；曳光弹起 MUST |
| `.github/workflows/ci.yml` | 每个 PR 和推到 main 时跑 `scripts/check --ci` | 原型 SHOULD；曳光弹起 MUST（M-08） |
| `scripts/agent-stop-hook` | agent 结束前跑 `scripts/check --if-changed`，没过就让它接着改 | SHOULD（三种 agent 共用） |
| `.claude/settings.json` | Claude Code：Stop hook；deny 读 `.env`、force push、`--no-verify`；改门禁文件要你点头 | 用 Claude Code 时 |
| `.cursor/hooks.json` | Cursor：stop hook 调同一个脚本 | 用 Cursor 时 |
| `.cursor/rules/mandatory.mdc` | Cursor：Always Apply 规则，指向 AGENTS.md 的强制项 | 用 Cursor 时 |
| `.codex/hooks.json` | Codex：Stop hook 调同一个脚本 | 用 Codex 时 |

分支保护不是文件，要在 GitHub 网页上设置，见第 4 节。长期档 MUST。

## 2. 装上（每个项目做一次）

1. 复制：`cp -R <本 skill>/templates/project/. <你的项目>/`，然后 `chmod +x scripts/check scripts/agent-stop-hook`。
2. 填 `scripts/check.conf`：`TIER`（demo / tracer / long，和 AGENTS.md 一致）、`REAL_DATA`、`PUBLIC`、`RUN_CMD`、`TEST_CMD`、`INSTALL_CMD`。长期档再填 `LOG_CHECK_CMD`、`CORE_DIRS`。
3. 跑一次 `scripts/check`（Windows：`powershell -ExecutionPolicy Bypass -File scripts/check.ps1`）。按 FAIL 行的「Fix」补齐，直到最后一行是 `RESULT: PASS`。
4. 装 gitleaks（[安装说明](https://github.com/gitleaks/gitleaks#installing)）。原型没装只报 WARN；曳光弹起没装就是 FAIL。
5. 曳光弹起：先 `pip install pre-commit`（或 `pipx install pre-commit`），再在项目里跑 `pre-commit install`。
6. 推到 GitHub，确认 PR 上出现名为 `check` 的检查并且是绿的。
7. 长期档：按第 4 节把 `check` 设为 main 的必需检查。
8. 在 AGENTS.md 命令表的「全量检查」写 `scripts/check`，在「强制项」一节写同一个命令。
9. 做第 6 节的故意违规验证，把命令和退出码贴进 G0 门禁表。

CI 里要先装语言环境。`ci.yml` 里留了 `actions/setup-node` / `actions/setup-python` 的注释示例，按项目语言打开一个。

## 3. 每项检查强制什么

`scripts/check` 每行输出：编号、级别（按档位算出的 MUST / SHOULD）、状态、说明和改法。状态有 PASS、FAIL、WARN（SHOULD 没过，不挡）、WAIVED、N/A、MANUAL（机器查不了，要在门禁表里另附证据）。

| 编号 | 检查 | 原型 | 曳光弹 | 长期 |
| --- | --- | --- | --- | --- |
| M-01 | 是 git 仓库，至少有一次提交 | MUST | MUST | MUST；main 受保护报 MANUAL |
| M-02 | 有 README.md；README 里能找到 `RUN_CMD`（有 `TEST_CMD` 时也要能找到）；原型 / 曳光弹的第一个非空行写明档位（原型 / prototype / demo；曳光弹 / tracer） | MUST | MUST | MUST（不查第一行） |
| M-03（R-1） | `.env` 类文件没被跟踪；`.gitignore` 忽略 `.env`；有 `.env.example` | MUST，不可豁免 | 同左 | 同左 |
| M-03（R-1） | 内置规则扫已跟踪和未忽略的文件：私钥头、常见云 / 平台密钥格式、`password = "..."` 一类硬编码 | MUST，不可豁免 | 同左 | 同左 |
| M-03（R-1） | gitleaks 扫历史、暂存区、工作区、未跟踪文件 | 没装 WARN；扫到就 FAIL | 必须装 | 必须装 |
| M-09 | `APP_DIRS` 里每个依赖清单（package.json、pyproject.toml、Cargo.toml、go.mod、Gemfile、composer.json、pubspec.yaml、Package.swift、Podfile、requirements.txt 等）都有已提交的锁文件；requirements.txt 每行都用 `==` 锁死 | MUST | MUST | MUST |
| M-09 | `INSTALL_CMD` 按锁文件装：拒绝 `npm install`、不带 `--frozen-lockfile` / `--immutable` 的 yarn / pnpm、不带 `--locked` 的 `uv sync`；`--ci` 时真的跑一遍 | — | MUST | MUST |
| M-05 | 不吞错：空 `catch {}`、`.catch(() => {})`、Python `except ...: pass`、Go 空 `if err != nil {}` | MUST | MUST | MUST |
| M-04 | `CORE_DIRS` 里没有裸 `print` / `console.log` / `println` / `fmt.Print`（填了才查） | MUST | MUST | MUST |
| M-04 | `LOG_CHECK_CMD`（日志规则检查，见 [logging.md](logging.md)）退出码 0 | 填了才查 | 填了才查 | MUST，必须填 |
| LINT | `LINT_CMD`（依赖方向、no-empty 等 lint）退出码 0 | 填了才查 | 填了才查 | 填了才查 |
| M-06 | `TEST_CMD` 已填且退出码 0 | 没有测试：SHOULD；有测试但失败：MUST（挡住） | MUST | MUST |
| M-08 | 有 CI 配置调用 `scripts/check` | SHOULD | MUST | MUST；必需检查报 MANUAL |

不查、只提醒（输出 MANUAL 行）：M-07 审查、M-10 安全 8 条、M-11 数据安全（[D] 时提醒 R-2）、M-12 文档、M-13 / M-14 发布项。它们照常写进门禁表。

豁免：`docs/WAIVERS.md` 里状态为「有效」的行写了哪个 M 编号，那个编号的 FAIL 显示为 WAIVED，不挡。状态改成「已到期」或「已补齐」后恢复 FAIL。M-03（红线 R-1）永远不能豁免。脚本只认文件，不判断豁免是不是用户亲口说的；这一点靠审查。

档位没填或填错时，按曳光弹执行，第一行写 `tier not confirmed ... using tracer`。

三个参数：
- `--ci`：先跑 `INSTALL_CMD`（CI 里环境变量 `CI=true` 时自动打开）。
- `--fast`：跳过安装、lint、日志命令和测试。pre-commit 用。
- `--if-changed`：上次全量 PASS 之后没有任何改动，就直接退出 0。agent hook 用，避免每次回答都重跑测试。

这些检查是启发式的：会漏（换个写法的空 catch、不在规则里的密钥格式），也可能误报（注释里的示例）。误报时改代码或改规则，不要关检查；改规则要你同意，长期档写 ADR。

## 4. 分支保护：把 CI 变成合入的硬门槛

GitHub 官方步骤（[Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)）：

1. 仓库主页 → Settings → 侧栏「Code, planning, and automation」里的 Branches。
2. 「Branch protection rules」下点 Add classic branch protection rule；Branch name pattern 填 `main`。
3. 勾 Require a pull request before merging（M-01：main 只经 PR 合入）。长期项目涉及密钥、数据、权限、门禁的改动要人审时，再勾 Require approvals。
4. 勾 Require status checks to pass before merging，在搜索框里选 `check`（`ci.yml` 里的 job 名）。搜不到时，先让 CI 在任意一个 PR 上跑一次，再回来选。
5. 勾 Do not allow bypassing the above settings。官方写明：默认情况下，规则对仓库管理员不生效（[About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)）。不勾这一项，你自己（管理员）仍能直接合入。
6. 保存。

官方文档里另外三点（同一页面已核实）：
- 被跳过（skipped）的必需检查也算通过。所以不要给 `check` job 加 `if:` 条件。
- 多个工作流里有同名 job 时，必需检查的结果会混淆，可能挡住所有 PR。保持 job 名 `check` 唯一。
- 公开仓库用免费版就能开分支保护；私有仓库需要 GitHub Pro、Team 或企业版。

证据：设置页截图，或 `gh api repos/<owner>/<repo>/branches/main/protection` 的输出。GitHub 的 rulesets 也能做到同样的事，本模板没有覆盖。

## 5. agent hook：没过检查不让 agent 收工

三种 agent 共用 `scripts/agent-stop-hook`：跑 `scripts/check --if-changed`；通过就输出 `{}`；不通过就把 FAIL 行交回 agent，并要求它「修好再跑；需要你出手时，结尾写 未满足：M-xx」。

| agent | 配置文件 | 失败时会怎样 | 核实情况 |
| --- | --- | --- | --- |
| Claude Code | `.claude/settings.json` 的 `Stop` hook | 退出码 2 阻止 Claude 结束，stderr 作为原因交给 Claude，它会继续工作。官方设了上限：stop hook 连续让它继续 8 次（中间没有调用工具）后，下一次不再阻止 | 已核实（[Hooks reference](https://code.claude.com/docs/en/hooks)：Exit code 2 behavior per event；Stop input） |
| Cursor | `.cursor/hooks.json` 的 `stop` hook | 不能「阻止结束」。返回 `followup_message` 时，Cursor 会把它作为下一条用户消息自动提交，agent 接着干；默认最多自动续 5 次（`loop_limit`） | 已核实（[Cursor Hooks](https://cursor.com/docs/hooks)：stop、loop_limit）。项目 hook 从项目根目录运行 |
| Codex | `.codex/hooks.json` 的 `Stop` hook | 退出码 2（或 `decision: "block"`）不会拒绝这一轮，而是用原因自动生成一条继续的提示，Codex 接着干。项目里的 `.codex/` 要先被信任，新 hook 要在 `/hooks` 里审核信任后才会运行 | 已核实（[Codex Hooks](https://developers.openai.com/codex/hooks)：Stop；Review and trust hooks） |

还没核实：
- hook 脚本是 bash。Windows 上这三种 agent 怎么执行它，本模板没有测试。
- `scripts/check.ps1` 只在 Linux 的 PowerShell 7 上测过，没在 Windows PowerShell 5.1 上测过。

`.claude/settings.json` 里另有两类规则（[Claude Code 权限](https://code.claude.com/docs/en/permissions)，已核实规则按 deny → ask → allow 的顺序生效）：
- deny：读 `.env`、`git push --force`、`git commit --no-verify`。
- ask：改 `scripts/check*`、CI 工作流、pre-commit 配置、`.gitleaksignore`、`docs/WAIVERS.md`、`.claude/settings.json` 时，先问你。

官方也写明，deny 规则挡不住自己去读文件的脚本（例如 Python 或 Node 程序打开文件）；要彻底挡，得开 sandbox。

## 6. 故意违规验证（装好后做一次）

每条都应该让 `scripts/check` 退出 1，并点名对应编号。做完撤销改动。

1. 新建一个文件，写一行假的硬编码密钥（随机生成，不要用真的）→ M-03 FAIL。
2. `git add -f .env` → M-03 FAIL（R-1：env file tracked）。
3. 写一个空 `catch (e) {}` 或 `except: pass` → M-05 FAIL。
4. 删掉锁文件 → M-09 FAIL。
5. 让已有的测试失败 → M-06 FAIL（原型也挡）。曳光弹起：删掉 `ci.yml` → M-08 FAIL。
6. 长期：在 `CORE_DIRS` 里加一行 `console.log` → M-04 FAIL。
7. 推一个故意失败的 PR，确认 GitHub 上合入按钮被挡住（长期档）。

## 7. 限度（照实说）

- `git commit --no-verify` 能跳过 pre-commit。所以 pre-commit 只是第一道；真正的门是 CI 加分支保护。
- agent 或人都可能改 `scripts/check.conf` 或检查脚本本身让它变绿。Claude Code 的 ask 规则只管 Claude；其他情况靠 PR 审查：改门禁文件的 PR 要你本人看过。
- 没开分支保护（或管理员能绕过）时，红色的 CI 只是提醒，挡不住合入。
- 只有 M-01、M-02、M-03、M-04、M-05、M-06、M-08、M-09 的一部分能机器查。其余项靠门禁表和审查；门禁表里不能把它们写成「已被机器强制」。

## 8. 来源（本次已核实）

- gitleaks：命令（`git`、`dir`、`--pre-commit`、`--staged`）、pre-commit 用法、发布 v8.30.1：https://github.com/gitleaks/gitleaks 。gitleaks-action 扫组织的仓库需要许可证，所以 CI 模板直接下载官方发布的二进制文件，并用官方 checksums 文件校验。
- pre-commit：`language: unsupported`（4.4.0 起替代 `system`）、`minimum_pre_commit_version`：https://pre-commit.com/
- pre-commit-hooks v6.0.0：https://github.com/pre-commit/pre-commit-hooks
- GitHub 分支保护：https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule 、https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- actions/checkout、setup-node、setup-python 的 `v7` 标签：https://github.com/actions
- Claude Code hooks 与权限：https://code.claude.com/docs/en/hooks 、https://code.claude.com/docs/en/permissions
- Cursor hooks 与 rules：https://cursor.com/docs/hooks 、https://cursor.com/docs/rules
- Codex hooks：https://developers.openai.com/codex/hooks

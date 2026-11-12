# E9 依赖锁定

档位：锁文件必备；依赖审计和自动更新为长期。时机：开工；加依赖时。

类比：菜谱写「某某牌酱油 500ml」，而不是「随便什么酱油」，每次做出来味道才一样。

为什么：不锁版本，今天能跑的项目，明天换台电脑安装可能就跑不起来，而且很难查出原因。OWASP Top 10:2025 把 A03「Software Supply Chain Failures」排在第三，社区调查里正好一半的人把它排第一（[A03:2025](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)）。

## 最低版

1. 锁文件提交进仓库：`package-lock.json`、`pnpm-lock.yaml`、`uv.lock` 等，包管理器生成什么就提交什么。
2. 一个项目只用一个包管理器，不要同时出现两种锁文件。
3. CI 和重新安装时，用「按锁文件安装、锁文件不对就失败」的命令：
   - npm：`npm ci`，要求项目有 `package-lock.json`，用于 CI、测试和部署这类需要干净安装的场景（[npm ci](https://docs.npmjs.com/cli/v10/commands/npm-ci)）。
   - pnpm：在 CI 里，锁文件需要更新时安装会失败（frozen lockfile）（[pnpm install](https://pnpm.io/cli/install)）。
   - uv：`--locked`，锁文件不是最新时报错而不是自动更新（[uv: Syncing](https://docs.astral.sh/uv/concepts/projects/sync/)）。
4. AI 要加新依赖时，先问：真的需要吗？标准库或已有依赖能不能做？包名拼写对不对（防止装到名字相似的仿冒包）？

## 长期

- 开 Dependabot 或同类工具：有补丁的安全告警会自动开 PR（[GitHub: Dependabot security updates](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/about-dependabot-security-updates)）。
- 发布前跑包管理器自带的审计命令。不要自动执行强制修复（例如 `npm audit fix --force`），它可能跨大版本升级（addyosmani/agent-skills `security-and-hardening`，MIT，借思路）。
- 新依赖写清用途、许可证、替代方案（`agent-constraint-docs` 的 RULES §2）。

## 检查

- 机器：CI 用锁文件安装；清单和锁文件不一致就失败。
- 人：审查新依赖和锁文件的改动。

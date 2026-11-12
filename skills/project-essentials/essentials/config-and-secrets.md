# E4 密钥与配置

强制：M-03 · 三档都 MUST；密钥不进仓库是红线 R-1，不可豁免（级别以 `project-essentials` 的 MANDATORY.md 为准）。时机：开工；发布前。

类比：家门钥匙不能贴在门上。代码会被很多人和很多工具看到，钥匙要放在代码外面。

为什么：Twelve-Factor 要求配置和代码严格分开；检验方法是「代码库能否随时开源，而不泄露任何凭据」（[The Twelve-Factor App III. Config](https://12factor.net/config)）。真实案例：一位非技术背景的开发者公开分享用 AI 编辑器做的 SaaS 后，API key 被刷爆、订阅被绕过、数据库被乱写（[X 帖子，2025-03-17](https://x.com/leojrr/status/1901560276488511759)）。

## 最低版

1. 密钥（API key、数据库密码、token）放在 `.env` 文件里，代码从环境变量读。
2. `.env` 写进 `.gitignore`。**先加 ignore，再创建 `.env`。**
3. 提交一份 [`.env.example`](../templates/.env.example)：只有变量名和假值，告诉别人要配哪些。
4. 启动时检查必需的配置。缺了就报清楚缺哪个，然后退出，不要带着空值继续跑。
5. 前端代码（网页、扩展、移动端安装包）里的任何值，都等于公开。私密密钥只能放在服务端。

## 密钥已经进了仓库怎么办

1. **先换掉这个密钥**（在服务商后台作废旧的、生成新的）。推到远端的那一刻起，就要当它已经泄露（addyosmani/agent-skills `security-and-hardening`，MIT，借思路：先轮换，再清历史）。
2. 再处理历史。只在下一个提交里删掉文件没用，历史里还在。
3. 文件已经被 git 跟踪时，加进 `.gitignore` 不会生效，要先 `git rm --cached <文件>`（[GitHub: Ignoring files](https://docs.github.com/en/get-started/git-basics/ignoring-files)）。

## 曳光弹 + 长期

- 打开 GitHub 的 push protection：推送里有已知格式的密钥时，直接拦下这次推送，而不是事后告警（[GitHub: Push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)）。
- 本地提交前钩子或 CI 跑密钥扫描（例如 gitleaks）。
- 给 agent 加 deny 规则，不许读 `.env`（见 `architecture-guardrails` 的 hooks）。
- 不同环境（开发 / 正式）用不同的密钥；密钥要能换、知道谁能看（[OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)）。

## 检查

- 机器：密钥扫描；push protection；启动时缺配置就失败的测试。
- 人：发布前确认前端包里没有私密密钥；`.env.example` 和实际用到的变量一致。

# E10 安全基础（新手版 8 条）

强制：M-10 · [P] 三档都 MUST，只要别人能访问到（网站、接口、发布的扩展或应用）；长期另做 OWASP ASVS L1 自查，为 SHOULD（级别以 `project-essentials` 的 MANDATORY.md 为准）。时机：开工；发布前。

类比：开店要锁门、收银台要有人看着，不能假设「顾客都会自觉」。

为什么：OWASP Top 10:2025 排第一的是 A01「Broken Access Control」（访问控制失效），第五是 A05「Injection」（注入）（[OWASP Top 10:2025](https://owasp.org/Top10/2025/)）。真实案例：公开分享项目后，API key 被刷爆、订阅被绕过、数据库被乱写（[X 帖子，2025-03-17](https://x.com/leojrr/status/1901560276488511759)）。

这里只列新手最常踩的 8 条。要做得更深，读 OWASP 原文。

## 8 条

1. **校验放在服务端**。浏览器里的校验可以被绕过，只用来给用户即时提示（[OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)）。
2. **每个请求都检查权限，默认拒绝**。用户只能读写自己的数据；只给完成工作需要的最小权限（[OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)：Enforce Least Privileges、Deny by Default、Validate the Permissions on Every Request）。
3. **数据库查询用参数化**，不要把用户输入拼进 SQL（[OWASP Query Parameterization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html)）。
4. **密钥不进前端、不进仓库**。见 [config-and-secrets.md](config-and-secrets.md)。
5. **花钱的接口加限流和费用上限**：调用模型服务、发短信、发邮件这类按次收费的接口，按用户限流，并在服务商后台设置用量上限。
6. **模型输出当作不可信的输入**。不直接放进 `eval`、SQL、shell 命令、`innerHTML` 或文件路径；先校验再用（[OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)：把模型当作任何其他用户，采用零信任）。
7. **登录、密码、加密用成熟方案**，不自己写。
8. **出错时不泄露内部信息**：用户只看到人话和错误编号。见 [errors.md](errors.md)。

第 5 条的做法参考了 addyosmani/agent-skills `security-and-hardening`（MIT，借思路），具体额度按项目定。

## 长期 + 对外：ASVS L1 自查（SHOULD）

8 条是 MUST。长期项目且别人能访问时，再对照 OWASP ASVS 的 Level 1 自查一遍。ASVS 把 L1 定为保护应用的最低要求（[OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)）。这是 SHOULD：结果写进 G3 门禁表，没做完不拦发布。

## 检查

- 机器：密钥扫描；依赖审计；lint 禁止 `eval` 和把变量拼进 `innerHTML`；权限测试：用户 A 读用户 B 的数据，应当被拒绝。
- 人：发布前逐条过一遍，每条写 PASS（附证据）/ FAIL / N/A；未核实按 FAIL 算。结果写进 G3 门禁表。

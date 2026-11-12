# Hook 与 deny 规则

只把没有例外的动作放进 hook。例子：

- 写完文件后自动格式化（PostToolUse）
- 拒绝读取 `.env` 或密钥目录
- 拒绝直接修改生成目录或迁移目录（除非任务明确是迁移）

检查项要少。把爱好写成 hook 会让环境又脆又吵。Hook 失败时的提示同样要写成改法。

「没过 `scripts/check` 不让 agent 收工」的 Stop hook 和 deny / ask 规则，现成模板见 [mandatory-gates.md](mandatory-gates.md) 第 5 节。

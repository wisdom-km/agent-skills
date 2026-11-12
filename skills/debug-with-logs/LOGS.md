# 能定位问题的日志

目标：界面上出错时给出一个**错误编号**；拿着这个编号在日志里一搜，就能看到这次操作经过了哪几层、在哪一层失败、为什么失败。

类比：日志像飞机的黑匣子，request_id 像病历号。出了事，按病历号调出这一个病人的全部记录，而不是翻整个医院的档案。

项目里「记哪些事件、用哪几个级别」写在 `ARCHITECTURE.md` 的日志节。本文件讲每一条日志该长什么样、怎么找、怎么读。

## 1. 最少字段（14 个）

| 字段 | 含义 | 为什么要 | 例子 |
| --- | --- | --- | --- |
| `time` | 带时区的时间（ISO 8601） | 排先后；对上用户说的时间 | `2026-03-02T21:05:41.120+08:00` |
| `level` | ERROR / WARN / INFO / DEBUG | 先看 ERROR | `ERROR` |
| `event` | 固定的事件名，snake_case | 能搜、能统计，不靠自然语言 | `todo_save_failed` |
| `request_id` | 一次用户操作的编号，入口生成，一路传 | 把散在各层的日志串成一条线 | `r-7f3a9c` |
| `module` | 哪一层、哪个模块 | 一眼看出断在哪 | `adapter.db` |
| `op` | 正在做的操作 | 上下文 | `save_todo` |
| `outcome` | ok / error / retry / skipped | 快速扫结果 | `error` |
| `duration_ms` | 耗时；外部调用必带 | 慢、超时类问题 | `5003` |
| `error.type` | 错误类型 | 知道是哪类错 | `TimeoutError` |
| `error.message` | 错误原因 | 知道「为什么」 | `db query timed out after 5000ms` |
| `error.stack` | 堆栈；只在 ERROR 时带 | 知道「哪一行」 | 多行文本，放在一个字段里 |
| `error.cause` | 被包装的原始错误 | 看到最底层原因 | `ECONNREFUSED` |
| `version` | 应用版本 | 对上是哪个版本出的错 | `0.4.2` |
| `env` | 运行环境和平台 | 「我这里是好的」类问题 | `prod` / `dev`，再加系统、浏览器 |

另外可以带**输入摘要**：ID、长度、数量，**不带内容**。例如 `todo_id=t-118, title_chars=42`。

绝不记：密码、token、API key、session 值、连接串、加密密钥、银行卡、个人敏感数据、整段请求体或响应体。外部输入写进日志前去掉换行符，防日志注入（[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)；OWASP 要求每条事件记下 when、where、who、what，并有一个把一次交互串起来的 interaction identifier）。

## 2. 坏日志和好日志

坏：

```text
Error!
save failed
[object Object]
user alice@example.com token sk-123 failed to save
```

问题：不知道是哪一次操作、哪一层、为什么；没法按编号搜；最后一行还泄露了邮箱和密钥。

好（JSON，一行一个事件）：

```json
{"time":"2026-03-02T21:05:36.010+08:00","level":"INFO","event":"todo_save_requested","request_id":"r-7f3a9c","module":"ui.todo_form","op":"save_todo","todo_id":"t-118","title_chars":42,"version":"0.4.2","env":"dev"}
{"time":"2026-03-02T21:05:36.015+08:00","level":"INFO","event":"db_query_started","request_id":"r-7f3a9c","module":"adapter.db","op":"insert_todo"}
{"time":"2026-03-02T21:05:41.018+08:00","level":"ERROR","event":"db_query_failed","request_id":"r-7f3a9c","module":"adapter.db","op":"insert_todo","outcome":"error","duration_ms":5003,"error":{"type":"TimeoutError","message":"db query timed out after 5000ms","cause":"ECONNREFUSED","stack":"TimeoutError: db query timed out after 5000ms\n    at insertTodo (db/todos.ts:57)\n    at saveTodo (core/save-todo.ts:23)"},"version":"0.4.2","env":"dev"}
{"time":"2026-03-02T21:05:41.020+08:00","level":"INFO","event":"todo_save_completed","request_id":"r-7f3a9c","module":"api.todos","op":"save_todo","outcome":"error","duration_ms":5010}
```

同样内容的 key=value 写法，在终端里更好读：

```text
2026-03-02T21:05:41.018+08:00 ERROR db_query_failed request_id=r-7f3a9c module=adapter.db op=insert_todo duration_ms=5003 error.type=TimeoutError error.message="db query timed out after 5000ms" error.cause=ECONNREFUSED
```

字段名和类型要固定，只是 JSON 还不算结构化（[OpenTelemetry Logs](https://opentelemetry.io/docs/concepts/signals/logs/)）。日志用结构化字段，不用字符串拼接（addyosmani/agent-skills `observability-and-instrumentation`，MIT，借思路）。

## 3. 错误日志的三条硬要求

新手最容易漏的三条：

1. **带堆栈**。只记 message 不够，要知道是哪一行。
   - Python：在 `except` 里用 `logger.exception(...)`，或给 `logger.error(...)` 传 `exc_info=True`（[Python logging](https://docs.python.org/3/library/logging.html)、[Logging HOWTO](https://docs.python.org/3/howto/logging.html)）。
   - JS / TS：记录 `err.stack`，不要只记 `err.message`，更不要直接拼接对象（会变成 `[object Object]`）。
2. **包装错误时保留原因**。往上抛一个更好懂的错误时，把原始错误带上。
   - JS / TS：`throw new Error("保存待办失败", { cause: err })`（[MDN `Error.cause`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/cause)）。
   - Python：`raise SaveTodoError("保存待办失败") from err`。
3. **同一个错误只记一次**。在最终处理它的地方记 ERROR；中间层只包装、往上抛，不要每层都记一遍（对应 RULES L-01）。

用户看到的错误和日志里的错误不一样：用户看到人话加错误编号，例如「保存失败，请稍后重试（错误编号 r-7f3a9c）」；堆栈只进日志，不给用户看（[OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)：出现意外错误时给用户通用回复，细节记在服务端日志里）。

## 4. request_id 从头到尾走一遍

例子：待办应用里，用户点「保存」。

```text
用户点「保存」
  └─ 前端生成 request_id = r-7f3a9c，记 todo_save_requested
      └─ 发请求到后端，HTTP 头带 X-Request-Id: r-7f3a9c
          └─ 后端入口读取这个头（没有就自己生成），记 request_received
              └─ core 用例 saveTodo(request_id, …)
                  └─ 数据库适配器 insertTodo，记 db_query_started
                      └─ 超时 → 记 db_query_failed（ERROR，带堆栈、耗时、原因）
              └─ 后端返回错误，响应里带同一个 request_id，记 request_completed
      └─ 前端显示「保存失败，请稍后重试（错误编号 r-7f3a9c）」
```

用户把「r-7f3a9c」发给你，你在日志里搜它，就能看到上面每一层的记录。

怎么一路传：
- **跨进程、跨网络**：放进 HTTP 头或消息体（[OpenTelemetry Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)）。
- **同一进程里，不想每个函数都多一个参数**：Node 用 `AsyncLocalStorage`，它能在一次 web 请求的整个生命周期里存数据（[Node.js 文档](https://nodejs.org/api/async_context.html)）；Python 用 `contextvars`（[Python 文档](https://docs.python.org/3/library/contextvars.html)）；或者在入口创建一个带 request_id 的子 logger 往下传（addyosmani `observability-and-instrumentation` 的 `logger.child({ requestId })` 示例）。
- **有多个入口**（按钮、定时任务、命令行）：再加一个 `entry_point` 字段（同一 skill 的建议）。

## 5. 日志在哪看（按平台）

| 平台 | 日志在哪 | 怎么看 | 出处 |
| --- | --- | --- | --- |
| 网页前端 | 浏览器 DevTools 的 Console；请求在 Network 面板 | F12 打开 DevTools → Console，在过滤框粘贴错误编号；Network 里看失败的请求 | [Chrome DevTools Console](https://developer.chrome.com/docs/devtools/console/log) |
| 服务端 / 本地后端 | 进程写到 stdout，本地就在运行它的终端；部署后由运行平台收集 | 看终端；需要存文件时 `npm run dev > app.log 2>&1`；部署后用平台的日志页面 | [The Twelve-Factor App XI. Logs](https://12factor.net/logs) |
| 浏览器扩展（Chrome） | ① `chrome://extensions` 里扩展卡片的 **Errors** 按钮（只记录运行时错误和 `console.warn` / `console.error`）② 后台 service worker：点「Inspect views」旁的链接打开它自己的 DevTools ③ popup：右键 popup → 检查 ④ content script：跑在网页里，要打开**那个网页**的 DevTools，在 Console 顶部的下拉框里选你的扩展 | 分别看对应 DevTools 的 Console | [Chrome 扩展调试教程](https://developer.chrome.com/docs/extensions/get-started/tutorial/debug) |
| 桌面应用（Electron） | `app.getPath('logs')`；macOS 默认 `~/Library/Logs/<应用名>`，Linux / Windows 在 `userData` 目录里 | 打开这个目录看日志文件；崩溃转储在 `app.getPath('crashDumps')` | [Electron `app`](https://www.electronjs.org/docs/latest/api/app) |
| 命令行工具 | 日志和错误写 **stderr**，正常结果写 stdout | 终端里看；`mytool ... 2> debug.log` 把日志存下来；提供 `--verbose` 或 `LOG_LEVEL=debug` | [Command Line Interface Guidelines](https://clig.dev/) |
| iOS / macOS 原生应用 | 系统的统一日志（unified logging）。代码里用 `Logger`，按 subsystem 和 category 分类 | ① 用 Xcode 运行并连着调试器时，Xcode 自动显示日志 ② macOS 的「控制台」（Console）App 查看、搜索 ③ 命令行 `log` 工具 ④ 已发布的版本没法用 Xcode 调试，要看崩溃报告和设备日志 | [Logger](https://developer.apple.com/documentation/os/logger)、[Viewing log messages](https://developer.apple.com/documentation/os/viewing-log-messages)、[Console 使用手册](https://support.apple.com/guide/console/welcome/mac)、[Diagnosing issues using crash reports and device logs](https://developer.apple.com/documentation/xcode/diagnosing-issues-using-crash-reports-and-device-logs) |
| Android 原生应用 | Logcat。代码里用 `Log` 类写日志 | ① Android Studio：View > Tool Windows > Logcat；应用抛异常时，Logcat 会显示堆栈并链接到代码行；可用 `package:mine`、`level:ERROR` 过滤 ② 命令行：`adb logcat`（是 `adb shell logcat` 的简写） | [View logs with Logcat](https://developer.android.com/studio/debug/logcat)、[Logcat 命令行工具](https://developer.android.com/tools/logcat)、[`android.util.Log`](https://developer.android.com/reference/android/util/Log) |
| React Native | React Native DevTools 的 Console 面板；应用内的 LogBox 会弹出错误和警告 | Dev Menu 里选「Open DevTools」，或在命令行按 `j`。官方建议以 DevTools 的 Console 为准。这些调试功能在 release 版本里关闭 | [React Native Debugging Basics](https://reactnative.dev/docs/debugging) |
| Flutter | DevTools 的 Logging view，或系统控制台 | `print()` 写 stdout；`dart:developer` 的 `log()` 信息更细；输出太多被丢行时用 `debugPrint()` | [Flutter code debugging](https://docs.flutter.dev/testing/code-debugging)、[Logging view](https://docs.flutter.dev/tools/devtools/logging) |

隐私提醒（移动端同样适用）：Apple 的 `Logger` 默认会把插值进去的字符串打码，防止用户信息进日志；Apple 也建议日志尽量只用你自己定义的固定字符串和数字（[Logger](https://developer.apple.com/documentation/os/logger)、[Generating log messages from your code](https://developer.apple.com/documentation/os/generating-log-messages-from-your-code)）。

把你项目用的那一行抄进 `AGENTS.md` 的命令表「看日志」。

## 6. 怎么搜、怎么读

搜（按项目实际的日志位置替换 `app.log`）：

```bash
rg 'r-7f3a9c' app.log                                  # 按错误编号找这一次请求的所有行
jq -c 'select(.request_id=="r-7f3a9c")' app.log        # JSON 日志按字段过滤
jq -c 'select(.level=="ERROR")' app.log | tail -n 20   # 没有编号时，先看最近的 ERROR
tail -f app.log                                        # 一边操作一边看
```

在 DevTools 里：Console 的过滤框粘贴错误编号；级别下拉只勾 Errors。

读：按时间顺序看这一个 request_id 的所有行，回答三个问题：
1. **第一条 ERROR 是哪条？** 不是最后一条。后面的错误常常是第一条引起的。
2. **它前面最近的外部调用是什么？** 数据库、网络、模型服务、文件。看它的耗时和结果。
3. **断在哪一层？** 看 `module`：`ui.*`、`api.*`、`core.*`、`adapter.*`。

读不出来，说明缺日志。在可疑的边界补「进入了什么、出来了什么、耗时多少」，再复现一次（obra/superpowers `systematic-debugging`：多组件系统先在每个边界加诊断日志，跑一次看断在哪）。

## 7. 可选：「复制诊断信息」按钮

本节是本 skill 自己的建议，不来自上面的出处。

客户端应用（网页前端、扩展、桌面、移动端）可以在内存里保留最近几百条日志，在设置页或错误提示旁放一个「复制诊断信息」按钮，一键复制：版本号、平台、最近的错误编号、最近 N 条日志（已去掉密钥和个人信息）。这样不会用 DevTools 的人，也能把日志交给 AI 或开发者。

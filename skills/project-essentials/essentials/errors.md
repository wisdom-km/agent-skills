# E7 错误处理与用户看到的错误信息

档位：必备。时机：开工；每个任务。

类比：餐厅后厨出了事，服务员对客人说「这道菜今天做不了，换一道吧，单号 37」，不会把后厨的事故记录拿给客人看。但后厨自己要有完整记录。

为什么：OWASP 建议出现意外错误时给用户一个通用回复，详细信息记在服务端日志里供排查，不返回给用户（[OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)）。OWASP Top 10:2025 新增了 A10「Mishandling of Exceptional Conditions」，专门讲错误处理不当、逻辑错误和失败时放行（failing open）（[A10:2025](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/)）。

## 最低版

1. **不吞错**：不写空 catch。捕获了就要么处理掉并记 WARN，要么带上下文往上抛。
2. **用户看到三样东西**：发生了什么（人话）、能做什么（重试、换个输入、联系谁）、**错误编号**（就是日志里的 request_id）。例如：「保存失败，请稍后重试（错误编号 r-7f3a9c）」。
3. **堆栈只进日志**，不显示给用户，不放进接口返回。日志写法见 `debug-with-logs` 的 LOGS.md。
4. **出错时默认拒绝**：权限检查、支付校验这类判断出了异常，按「不允许」处理，不要按「允许」放行。

## 全局兜底

保证没有错误「无声消失」。按平台选一种：

| 平台 | 兜底方式 | 出处 |
| --- | --- | --- |
| 网页前端 | 监听 `error` 和 `unhandledrejection` 事件，记录并显示通用错误提示 | [MDN error 事件](https://developer.mozilla.org/en-US/docs/Web/API/Window/error_event)、[MDN unhandledrejection](https://developer.mozilla.org/en-US/docs/Web/API/Window/unhandledrejection_event) |
| React 界面 | 用 Error Boundary 显示备用界面；它不捕获事件处理函数里的错误，那些要自己 try/catch | [React: Catching rendering errors with an Error Boundary](https://react.dev/reference/react/Component) |
| Node 服务 | 框架的全局错误处理中间件；`uncaughtException` 只用来记录和清理，之后退出进程，由外部重启（官方说明：发生后继续正常运行是不安全的） | [Node.js process](https://nodejs.org/api/process.html) |
| Python | 框架的全局异常处理；脚本可设置 `sys.excepthook` 把未捕获的异常记进日志 | [Python sys](https://docs.python.org/3/library/sys.html) |

## 检查

- 机器：空 catch lint（`architecture-guardrails` 的 `recipes/logging.md`）；测试断言错误响应里没有堆栈字段；测试断言出错时界面显示错误编号。
- 人：每个用户能看到的错误都有人话和编号；权限相关的异常分支是「拒绝」。

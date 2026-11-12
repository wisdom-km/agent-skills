# E12 健康检查与崩溃上报

档位：可选，上线给别人用之后建议做。时机：发布前。

类比：家里装烟雾报警器，不用等闻到烟味才知道着火。

为什么：用户遇到问题时，大多数不会告诉你。监控要回答两个问题：坏了什么、为什么坏；最该看的是四个黄金信号：延迟、流量、错误、饱和度（[Google SRE Book 第 6 章](https://sre.google/sre-book/monitoring-distributed-systems/)）。

本文件不推荐具体厂商。选第三方服务前，先看它会收集哪些数据、会不会带走用户的个人信息、密钥怎么放。

## 健康检查（有服务端时）

- 提供一个 `/health` 接口：进程活着、能连上必需的依赖（数据库等）就返回成功。
- 运行平台可以用它判断要不要重启。例如 Kubernetes 用 liveness probe 发现「进程还在、但已经坏了、只能重启才能恢复」的情况（[Kubernetes: Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)）。
- 健康检查的返回里不放密钥、连接串和内部细节。

## 崩溃和错误上报（客户端）

按平台选：

| 平台 | 做法 | 出处 |
| --- | --- | --- |
| 网页前端 | 全局监听 `error` 和 `unhandledrejection`，把错误编号、版本、平台和脱敏后的错误发到你自己的接口 | [MDN error 事件](https://developer.mozilla.org/en-US/docs/Web/API/Window/error_event)、[MDN unhandledrejection](https://developer.mozilla.org/en-US/docs/Web/API/Window/unhandledrejection_event) |
| Electron 桌面 | `crashReporter` 可以把崩溃报告提交到远端服务器 | [Electron crashReporter](https://www.electronjs.org/docs/latest/api/crash-reporter) |
| iOS / macOS | 系统会收集崩溃报告；发布版（App Store、测试分发）没法用 Xcode 调试，要靠崩溃报告和设备日志排查 | [Diagnosing issues using crash reports and device logs](https://developer.apple.com/documentation/xcode/diagnosing-issues-using-crash-reports-and-device-logs) |
| Android | 开发时在 Logcat 看崩溃堆栈 | [View logs with Logcat](https://developer.android.com/studio/debug/logcat) |

上报的内容和日志一样：不带密钥、token、个人敏感数据。用户能看到的错误提示里给错误编号，上报里也带同一个编号，两边就能对上。

## 告警（可选）

- 错误率突然升高时通知你自己。先从一条告警开始，不要一次配很多。
- 告警要能指向下一步：去哪看日志、按哪个字段过滤。

## 检查

- 机器：健康检查接口有测试；上报的数据里没有密钥字段（同日志的字段名扫描）。
- 人：故意制造一次错误，确认上报收到了、错误编号能在日志里找到。

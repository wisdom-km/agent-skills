# 运行日志检查

目的：让 ARCH 里的日志规则（RULES L-01 到 L-05、N-01）不靠自觉。先在 ARCH 写清日志节，再做检查。工具按项目语言选，下面只是例子。

## 哪些能机器查

| 规则 | 能机器查吗 | 怎么查（例子） |
| --- | --- | --- |
| core 不用裸 print / console.log（L-03） | 能 | JS/TS：ESLint `no-console`，只对 core 目录开启。Python：Ruff `T201`（print）。其他语言用同等 lint 或 grep 脚本 |
| core 不 import 具体日志库（L-03） | 能 | 和依赖方向用同一个工具：ESLint `no-restricted-imports`、dependency-cruiser、import-linter 的 forbidden 契约。见 [dependency-boundaries.md](dependency-boundaries.md) |
| 不写空 catch（L-02） | 能 | JS/TS：ESLint `no-empty`。Python：Ruff `S110`（try-except-pass）、`BLE001`（捕获过宽的异常） |
| 不用字符串拼接写日志（L-05） | 部分能 | Python：Ruff `G004`（日志里用 f-string）。其他语言写自定义 lint：日志调用的第一个参数必须是固定字符串 |
| 日志不记密钥（N-01、L-05） | 部分能 | 密钥扫描（例如 gitleaks）扫代码和测试输出；自定义检查：日志调用的字段名里不能出现 password、token、secret、authorization、cookie |
| 每条日志带 request_id 和固定字段 | 部分能 | 契约测试：core 用内存 logger 假实现，跑一个用例，断言每条日志都有 request_id、event、level |
| 出错时有一条可定位的 ERROR（L-01） | 能 | 错误路径测试：让适配器假实现抛错，断言恰好有一条 ERROR，且带 request_id、event、error.type、error.message、error.stack。见下面「错误路径测试」 |
| 新边界有日志（L-04） | review | PR 模板「日志」一节；审查时对照 ARCH 事件表 |
| 错误的上下文够定位（L-01） | review | 故意触发一次错误，按 request_id 能找到原因。结果写进 PR 证据 |
| 级别用得对 | review | 对照 ARCH 级别表 |
| 不记个人敏感数据 | review | 字段名清单只能挡一部分，抽查真实输出 |

## 错误路径测试

只断言「出错时能定位」，不断言日志文案。字段名按 ARCH 日志节替换。

```ts
// test/core/save-todo.error-log.test.ts
it("logs one locatable ERROR when the db adapter fails", async () => {
  const logs = createMemoryLogger();                    // 内存 logger 假实现
  const db = failingDb(new Error("db down"));           // 适配器假实现：总是抛错
  await expect(saveTodo({ requestId: "r-test-1", db, logger: logs }, input)).rejects.toThrow();

  const errors = logs.entries.filter((e) => e.level === "ERROR");
  expect(errors).toHaveLength(1);                       // 同一个错误只记一次
  expect(errors[0]).toMatchObject({ request_id: "r-test-1", event: expect.any(String) });
  expect(errors[0].error?.type).toBeTruthy();
  expect(errors[0].error?.message).toBeTruthy();
  expect(errors[0].error?.stack).toBeTruthy();         // 有堆栈，能定位到行
});
```

Python 同理：用一个收集记录的 handler，断言 `record.levelname == "ERROR"`、`record.request_id`、`record.exc_info` 不为空。

报错写成改法，例如：「L-01：`saveTodo` 出错时没有 ERROR 日志，或缺 `error.stack`。在最终处理错误的地方调用 `logger.error({ event, request_id, error })`，`error` 里带 stack；中间层只包装往上抛。见 ARCHITECTURE §10。」

故意违规验证：把 `logger.error` 那行删掉，或只记 `err.message`，这条测试应当失败。

## 做法

1. 能查的规则接到一条本地命令和 CI，命令写进 `AGENTS.md` 命令表。
2. 报错写成改法，例如：「L-03：`core/order/submit.ts` 调用了 `console.log`。改为使用注入的 `logger.error({ event, request_id, ... })`。见 ARCHITECTURE §10。」
3. 用故意违规的样例证明检查会拒绝：core 里加一行 print、一个空 catch、一个记 password 的日志调用。
4. 只能 review 的规则，在 RULES 的「怎么拦」列写 review，不写成已强制。
5. 检查不要管选哪个日志库。只查不变量：core 不直连、不吞错、不记密钥、结构化。

出处：[Harness Engineering](https://openai.com/index/harness-engineering/)（自定义 lint 静态强制结构化日志，报错里写改法）；[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)（不记的数据、防日志注入）。

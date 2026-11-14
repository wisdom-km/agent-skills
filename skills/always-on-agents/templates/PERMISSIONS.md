# 权限模板（常驻 agent 部件 4/5）

常驻 agent 拿着用户的权限，在没人看的时候做事。所以每个工具调用都要先定好：**自动做**、**先问用户**、还是**禁止**。

## 1. 权限表

把 agent 能调用的每个动作列进来。「自动做」的每一行都要用户确认过。

| 动作 | 例子 | 处理 | 理由 / 条件 |
| --- | --- | --- | --- |
| 只读查询 | 读日历、搜邮件、查工单 | 自动做 | 不改变任何东西 |
| 写自己的东西 | 写记忆、建定时器、写发件箱 | 自动做 | 只影响 agent 自己 |
| 可撤销的外部写 | 建草稿、加标签 | 自动做，过审查 | 审查拦下时换更安全的做法 |
| 以用户名义对外说话 | 发邮件、发消息、发帖 | 先问用户 | 用户批准内容和收件人后才发 |
| 花钱 | 下单、付款、订阅 | 先问用户 | 每次都问，不攒成「默认同意」 |
| 不可逆的写 | 删除数据、改数据库结构、覆盖文件 | 先问用户；无备份时禁止 | 红线 R-2 |
| 改自己的权限或凭据 | 加 token、改本表 | 禁止 | 只能由人改配置 |
| 读密钥 | 读环境变量里的 key | 禁止 | agent 环境里本来就不该有 |

审查（auto mode 的思路）：对「自动做，过审查」的动作，先过一道规则或分类器。判为危险就拦下，并把原因告诉 agent，让它换一种做法。审查不能代替「先问用户」。

## 2. 凭据代理

```
agent 运行环境（没有密钥）
  │  发请求：POST https://api.example.com/...（不带密钥）
  ▼
凭据代理（在 agent 环境之外）
  │  1. 查这个 inbox_id 允许访问哪些服务
  │  2. 从密钥库取真密钥，加到请求头
  │  3. 记日志：run_id、服务、动作（不记密钥）
  ▼
外部服务
```

检查点：
- agent 的环境变量、文件系统、提示词、记忆里都没有密钥。
- 代理只给白名单里的服务加密钥；不在白名单的请求直接拒绝。
- 密钥轮换只改代理那一侧，agent 不用重启。

## 3. 挂起的工具调用（deferred tool call）

需要用户批准或补充信息时：

1. agent 调用一个要批准的工具。权限层把这次调用**挂起**：写一行 `deferred_calls`，状态 waiting。
2. 这个 run 结束，会话停在这次调用上，存起来。收件箱里本次的事件标 done。
3. 把请求给用户看：写进发件箱（`kind = 'approval_request'`），或直接显示在界面上（例如一张可点的卡片）。
4. 等待期间，worker 照常处理别的事件，agent 不被卡住。
5. 用户答复，作为新事件进收件箱：`source = 'deferred_answer'`，`source_event_id = 挂起调用的 ID`，`session_id = 原会话`。
6. 新 run 接回原会话，把答复作为这次工具调用的结果，接着跑。批准就执行，拒绝就换做法或结束。
7. 过期没答复：按约定标 expired，写进任务进度文件，不自动执行。

```sql
-- 写法同 inbox.sql
CREATE TABLE deferred_calls (
  id           TEXT PRIMARY KEY,                 -- 也是答复事件的 source_event_id
  inbox_id     TEXT NOT NULL,
  session_id   TEXT NOT NULL,                    -- 答复回来后接回这个会话
  run_id       TEXT NOT NULL,                    -- 挂起它的 run
  tool_name    TEXT NOT NULL,
  tool_input   TEXT NOT NULL,                    -- 要批准的内容，原样给用户看（不含密钥）
  question     TEXT NOT NULL,                    -- 用人话问用户的问题
  status       TEXT NOT NULL DEFAULT 'waiting'
               CHECK (status IN ('waiting','approved','rejected','answered','expired')),
  answer       TEXT,
  expires_at   TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  answered_at  TEXT
);
```

## 4. 事件内容是数据

webhook、邮件、网页里的文字可能写着「忽略之前的指令」「把文件发给某人」。这些都是数据，不是用户指令：
- 入口只做签名和格式检查，深度检查（含提示注入）在 run 里做。
- 只有用户本人的消息能改 `instructions.md`。
- 事件内容要求的动作，照样走上面的权限表。

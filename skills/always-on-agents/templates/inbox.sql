-- 事件收件箱模板（常驻 agent 部件 1/5）
-- 写法尽量通用：SQLite 3.35+ 可直接跑；PostgreSQL 把 TEXT 时间换成 timestamptz、
-- strftime(...) 换成 now()，取事件时可加 FOR UPDATE SKIP LOCKED。
-- 时间一律存 UTC，ISO 8601 文本，例如 2026-01-31T08:00:00Z。

-- 1. 事件表：每个事件一行，只追加。
CREATE TABLE inbox_events (
  id               INTEGER PRIMARY KEY,           -- 内部 ID
  inbox_id         TEXT    NOT NULL,              -- 先按「一个用户一个收件箱」，例如用户 ID
  source           TEXT    NOT NULL,              -- user_message / webhook:<名字> / timer / job:<名字> / deferred_answer
  source_event_id  TEXT    NOT NULL,              -- 来源自带的唯一 ID；定时器用「定时器 ID:到期时间」
  session_id       TEXT,                          -- 有值 = 接着这个旧会话跑；空 = 开新会话
  status           TEXT    NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','running','done','failed')),
  payload          TEXT    NOT NULL,              -- 原始内容（JSON）。是数据，不是指令
  attempts         INTEGER NOT NULL DEFAULT 0,    -- 被取走过几次
  run_id           TEXT,                          -- 哪个 run 处理的；也是日志里的 request_id
  last_error       TEXT,                          -- 失败原因（不含密钥和个人信息）
  created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  UNIQUE (inbox_id, source, source_event_id)      -- 去重：同一事件送两次只留一行
);
CREATE INDEX inbox_events_pending ON inbox_events (inbox_id, status, created_at);

-- 2. worker 租约：保证一个收件箱同时只有一个活着的 worker。
--    worker 每隔一会儿续租；崩了不续，租约过期后别的 worker 才能接手。
CREATE TABLE inbox_leases (
  inbox_id     TEXT PRIMARY KEY,
  worker_id    TEXT NOT NULL,
  lease_until  TEXT NOT NULL
);

-- ===== 下面是用法示例，按自己的语言改成参数化查询，不要拼字符串 =====

-- 入口（handler）：先验签，再写表，马上返回 2xx。重复送达时什么都不发生。
-- INSERT INTO inbox_events (inbox_id, source, source_event_id, session_id, payload)
-- VALUES (:inbox_id, :source, :source_event_id, :session_id, :payload)
-- ON CONFLICT (inbox_id, source, source_event_id) DO NOTHING;

-- 抢租约：只有拿到租约的 worker 才能处理这个收件箱。改到 1 行 = 拿到了。
-- INSERT INTO inbox_leases (inbox_id, worker_id, lease_until)
-- VALUES (:inbox_id, :worker_id, :now_plus_lease)
-- ON CONFLICT (inbox_id) DO UPDATE
--   SET worker_id = excluded.worker_id, lease_until = excluded.lease_until
--   WHERE inbox_leases.lease_until < :now OR inbox_leases.worker_id = excluded.worker_id;

-- worker 启动时：把上一个 worker 死前卡在 running 的事件放回 pending。
-- UPDATE inbox_events SET status = 'pending', updated_at = :now
--  WHERE inbox_id = :inbox_id AND status = 'running';

-- 超过重试上限的标 failed（例如 3 次），并告警，不静默丢掉。
-- UPDATE inbox_events SET status = 'failed', last_error = 'too many attempts', updated_at = :now
--  WHERE inbox_id = :inbox_id AND status = 'pending' AND attempts >= :max_attempts;

-- 取一批：把这个收件箱所有 pending 一次取走，合成一个 run（连发三条只回一次）。
-- UPDATE inbox_events
--    SET status = 'running', attempts = attempts + 1, run_id = :run_id, updated_at = :now
--  WHERE inbox_id = :inbox_id AND status = 'pending'
-- RETURNING id, source, session_id, payload;
-- 取回的事件按 session_id 分组：有 session_id 的接旧会话，没有的开新会话。

-- run 正常结束（发了消息、什么都没发、或挂起了工具调用）：
-- UPDATE inbox_events SET status = 'done', updated_at = :now WHERE run_id = :run_id;

-- run 出错：放回 pending 等下次重试，并记下原因。
-- UPDATE inbox_events SET status = 'pending', last_error = :error, updated_at = :now WHERE run_id = :run_id;

-- 定时器模板（常驻 agent 部件 2/5）
-- 定时器单独一张表，不放进收件箱。定时器自己不启动 run：
-- scheduler 按固定间隔扫表，把到点的定时器变成收件箱里的一个事件。
-- 写法同 inbox.sql：SQLite 3.35+ 可直接跑；PostgreSQL 换时间类型即可。时间存 UTC。

CREATE TABLE timers (
  id            TEXT    PRIMARY KEY,             -- 例如 tmr_01H...
  inbox_id      TEXT    NOT NULL,                -- 到点后写进哪个收件箱
  kind          TEXT    NOT NULL CHECK (kind IN ('follow_up','schedule')),
                                                 -- follow_up：agent 给自己定的一次性截止时间
                                                 -- schedule：固定节奏的周期任务
  due_at        TEXT    NOT NULL,                -- 下次到期时间（UTC）
  recurrence    TEXT,                            -- 只有 schedule 有：cron 表达式，例如 '0 8 * * *'
  timezone      TEXT,                            -- 只有 schedule 有：用户时区，例如 'Asia/Shanghai'
  session_id    TEXT,                            -- 跟进要接回的旧会话；周期任务通常为空（开新会话）
  status        TEXT    NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','done','cancelled')),
  payload       TEXT    NOT NULL,                -- 醒来要做什么，例如 {"task":"tasks/T-3.md","check":"对方回了没有"}
  created_by    TEXT    NOT NULL,                -- 'user' 或创建它的 run_id
  last_fired_at TEXT,
  created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  CHECK (kind = 'follow_up' OR (recurrence IS NOT NULL AND timezone IS NOT NULL))
);
CREATE INDEX timers_due ON timers (status, due_at);

-- ===== scheduler 每一轮（例如每 30 秒），在一个事务里做 =====

-- 1. 找出到点的定时器
-- SELECT id, inbox_id, kind, due_at, recurrence, timezone, session_id, payload
--   FROM timers WHERE status = 'active' AND due_at <= :now;

-- 2. 对每一个：往收件箱写事件。去重 ID = 定时器 ID + 本次到期时间，
--    scheduler 重跑或两个 scheduler 同时跑，也只会有一个事件。
-- INSERT INTO inbox_events (inbox_id, source, source_event_id, session_id, payload)
-- VALUES (:inbox_id, 'timer', :timer_id || ':' || :due_at, :session_id, :payload)
-- ON CONFLICT (inbox_id, source, source_event_id) DO NOTHING;

-- 3a. 跟进：标 done
-- UPDATE timers SET status = 'done', last_fired_at = :now WHERE id = :timer_id AND kind = 'follow_up';

-- 3b. 周期：把 due_at 挪到「现在之后」的下一次。下一次由代码按 recurrence + timezone 算，
--     换成 UTC 再写回。停机很久后恢复，只补发一次，不要把错过的每一次都补发。
-- UPDATE timers SET due_at = :next_due_at_utc, last_fired_at = :now WHERE id = :timer_id AND kind = 'schedule';

-- 4. 提交事务后叫醒 worker（通知、信号或让 worker 自己轮询都行）。

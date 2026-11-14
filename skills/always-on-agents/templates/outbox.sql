-- 发件箱模板（常驻 agent 部件 5/5）
-- 大多数场景一个「发送」工具直接发就够，不需要这张表。
-- 要控制节奏（合并、免打扰时段、每日上限）或要在发送失败时重试，才建它，并配一个 dispatcher。
-- 发送规则写在 SEND_POLICY.md。写法同 inbox.sql。

CREATE TABLE outbox_messages (
  id            INTEGER PRIMARY KEY,
  inbox_id      TEXT    NOT NULL,                 -- 发给哪个用户（与收件箱一一对应）
  run_id        TEXT    NOT NULL,                 -- 哪个 run 写的；日志用它串起来
  kind          TEXT    NOT NULL CHECK (kind IN ('message','approval_request')),
                                                  -- approval_request：挂起的工具调用要用户批准或补充信息
  priority      TEXT    NOT NULL DEFAULT 'normal' CHECK (priority IN ('urgent','normal','digest')),
  channel       TEXT    NOT NULL,                 -- 例如 chat / email / push
  body          TEXT    NOT NULL,                 -- 结果加几句要点，不是一步步的过程
  dedupe_key    TEXT    NOT NULL,                 -- 同一件事只发一次，例如 'task:T-3:done'
  status        TEXT    NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','sent','failed','suppressed')),
                                                  -- suppressed：dispatcher 按策略决定不发（要写 reason）
  reason        TEXT,                             -- 不发或失败的原因
  not_before    TEXT,                             -- 最早什么时候发（免打扰时段、合并窗口）
  attempts      INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  sent_at       TEXT,
  UNIQUE (inbox_id, dedupe_key)
);
CREATE INDEX outbox_pending ON outbox_messages (status, not_before);

-- ===== 用法示例 =====

-- run 结尾写一条（重复写同一件事会被 UNIQUE 挡住）：
-- INSERT INTO outbox_messages (inbox_id, run_id, kind, priority, channel, body, dedupe_key, not_before)
-- VALUES (:inbox_id, :run_id, 'message', 'normal', 'chat', :body, :dedupe_key, :not_before)
-- ON CONFLICT (inbox_id, dedupe_key) DO NOTHING;

-- dispatcher 每一轮：取到点的 pending，按 SEND_POLICY.md 决定发、合并或压下。
-- SELECT * FROM outbox_messages
--  WHERE status = 'pending' AND (not_before IS NULL OR not_before <= :now)
--  ORDER BY priority = 'urgent' DESC, created_at;

-- 发成功：
-- UPDATE outbox_messages SET status = 'sent', sent_at = :now WHERE id = :id;
-- 发失败：attempts + 1，没超上限就留在 pending 稍后重试；超了标 failed 并告警。
-- UPDATE outbox_messages SET attempts = attempts + 1,
--        status = CASE WHEN attempts + 1 >= :max_attempts THEN 'failed' ELSE 'pending' END,
--        reason = :error, not_before = :retry_at
--  WHERE id = :id;
-- 发出去的消息同时写进记忆的 told.md（见 MEMORY.md），防止下次重复说。

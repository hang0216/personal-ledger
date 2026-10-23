-- ============================================================
-- 个人记账本 · 选做功能数据库脚本（SQLite）
--
-- 适用范围：在已运行过原有 MVP 的数据库（categories / transactions）上增量执行。
-- 选做功能 1「预算提醒」需要新增 budgets 表；
-- 选做功能 2「账单搜索」、选做功能 3「数据导出」复用 transactions 表，
-- 无需新增字段与索引（date 已有索引，搜索走 date 范围 + note LIKE）。
--
-- 执行方式：
--   sqlite3 backend/ledger.db < backend/sql/optional_features.sql
-- 或：
--   python -c "import sqlite3;c=sqlite3.connect('backend/ledger.db');c.executescript(open('backend/sql/optional_features.sql',encoding='utf-8').read());c.commit()"
--
-- 说明：应用启动时 SQLAlchemy 的 create_all 也会幂等建表，
--       本脚本用于手工建库 / 交付评审 / 数据库变更留档。
-- ============================================================

-- ------------------------------------------------------------
-- 选做功能 1：月度预算表
--   month      业务月份，主键，格式 YYYY-MM（同一个月仅一条预算）
--   amount     预算金额，单位「分」（与 transactions.amount 口径一致）
--   created_at 创建时间（业务时区 Asia/Shanghai，YYYY-MM-DD HH:MM:SS）
--   updated_at 更新时间（覆盖设置预算时刷新）
--
-- 约束：
--   amount > 0 且 <= 9,999,999,999 分（即 99,999,999.99 元，与账单上限一致）
--   month 必须匹配 YYYY-MM
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budgets (
    month      TEXT    NOT NULL PRIMARY KEY,
    amount     INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    CONSTRAINT ck_budgets_amount CHECK (amount > 0 AND amount <= 9999999999),
    CONSTRAINT ck_budgets_month CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]')
);

-- ------------------------------------------------------------
-- 选做功能 2：账单搜索（无结构变更，仅确认查询用索引存在）
--   普通模式：WHERE date >= 月初 AND date < 次月初
--   搜索模式：WHERE date >= start AND date <= end AND note LIKE '%关键词%'
--             AND type = ? AND category_id = ?
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (date);
CREATE INDEX IF NOT EXISTS ix_transactions_type ON transactions (type);
CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON transactions (category_id);

-- ------------------------------------------------------------
-- 选做功能 3：数据导出（无结构变更）
--   导出为前端行为：把当前查询结果按 日期/类型/分类/金额/备注 生成 CSV，
--   不新增数据库对象，也不写入任何临时表。
-- ------------------------------------------------------------

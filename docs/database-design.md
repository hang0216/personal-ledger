# 个人记账本 — 数据库设计说明书（database-design.md）

| 项目 | 内容 |
| --- | --- |
| 文档类型 | 数据库设计 |
| 版本 | v1.1（新增选做功能预算表） |
| 日期 | 2026-10-21 |
| 数据库 | SQLite 3（单文件） |
| 实现依据 | `backend/app/models/*.py`、`backend/app/database/*.py` |
| 关联文档 | `spec.md`、`docs/architecture.md`、`docs/api-design.md`、`docs/optional-features-spec.md` |

---

## 1. 选型与总体结构

- **SQLite 单文件库**：个人记账、单机/单实例部署，零运维成本，直接备份文件即完成备份。
- **ORM**：SQLAlchemy 2.0（`DeclarativeBase`），应用启动时 `Base.metadata.create_all()` 幂等建表。
- **默认文件位置**：`backend/ledger.db`；可通过环境变量 `LEDGER_DB_PATH` 指向其他文件（测试/生产隔离）。
- **连接配置**：每条连接执行 `PRAGMA foreign_keys = ON`，保证 `ON DELETE RESTRICT` 生效。
- **时区**：所有时间字段由 SQLite `datetime('now', '+8 hours')` 或应用层 `Asia/Shanghai` 生成，格式 `YYYY-MM-DD HH:MM:SS`。

```
categories (1) ────< (N) transactions
      分类                    账单

budgets（独立表，按月份存放预算，不与账单建外键）
```

---

## 2. 表：categories（分类）

### 2.1 用途

存放收入/支出分类。预置 13 条，用户可新增、删除，不支持编辑/重命名。

### 2.2 结构

| 字段 | 类型 | 空 | 说明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 否 | 主键，自增（`AUTOINCREMENT`，删除后不复用） |
| `name` | TEXT | 否 | 分类名称，去首尾空格后 1–20 个 Unicode 码点 |
| `type` | TEXT | 否 | `income` / `expense` |
| `created_at` | TEXT | 否 | 创建时间，默认 `datetime('now','+8 hours')` |

### 2.3 DDL

```sql
CREATE TABLE IF NOT EXISTS categories (
    id         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    type       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    CONSTRAINT ck_categories_name_len CHECK (length(name) BETWEEN 1 AND 20),
    CONSTRAINT ck_categories_type     CHECK (type IN ('income', 'expense')),
    CONSTRAINT ux_categories_name_type UNIQUE (name, type)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_name_type
    ON categories (name, type);
```

> 唯一约束范围为 `(name, type)`：不同类型下允许同名分类。

---

## 3. 表：transactions（账单）

### 3.1 用途

存放每一笔收入/支出记录，是记账、搜索、报表的唯一数据源。

### 3.2 结构

| 字段 | 类型 | 空 | 说明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 否 | 主键，自增 |
| `amount` | INTEGER | 否 | 金额，单位**分**（> 0，≤ 9,999,999,999） |
| `type` | TEXT | 否 | `income` / `expense`，必须与分类 `type` 一致（应用层校验） |
| `category_id` | INTEGER | 否 | 外键 → `categories.id`，`ON DELETE RESTRICT` |
| `date` | TEXT | 否 | 业务日期 `YYYY-MM-DD`，≥ 2000-01-01 |
| `note` | TEXT | 是 | 备注，≤ 100 个 Unicode 码点 |
| `created_at` | TEXT | 否 | 创建时间 |
| `updated_at` | TEXT | 否 | 更新时间，编辑时由应用层刷新 |

### 3.3 DDL

```sql
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    amount      INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    category_id INTEGER NOT NULL,
    date        TEXT    NOT NULL,
    note        TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    CONSTRAINT ck_transactions_amount   CHECK (amount > 0 AND amount <= 9999999999),
    CONSTRAINT ck_transactions_type     CHECK (type IN ('income', 'expense')),
    CONSTRAINT ck_transactions_date     CHECK (
        date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND date >= '2000-01-01'
    ),
    CONSTRAINT ck_transactions_note_len CHECK (note IS NULL OR length(note) <= 100),
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_transactions_type        ON transactions (type);
CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON transactions (category_id);
CREATE INDEX IF NOT EXISTS ix_transactions_date        ON transactions (date);
```

### 3.4 索引说明

| 索引 | 支撑场景 |
| --- | --- |
| `ix_transactions_date` | 月度区间扫描、日期范围搜索、排序 |
| `ix_transactions_type` | 收入/支出筛选、报表分组 |
| `ix_transactions_category_id` | 分类筛选、分类引用检查、报表 JOIN |

> 备注关键词为 `LIKE '%kw%'` 模糊匹配，普通索引无法命中；个人记账数据量小，可接受全表扫描。

---

## 4. 表：budgets（月度预算，选做功能 1）

### 4.1 用途

按月份保存用户预算金额，每月最多一条；重复设置即覆盖。

### 4.2 结构

| 字段 | 类型 | 空 | 说明 |
| --- | --- | --- | --- |
| `month` | TEXT | 否 | 主键，`YYYY-MM` |
| `amount` | INTEGER | 否 | 预算金额，单位**分**（> 0，≤ 9,999,999,999） |
| `created_at` | TEXT | 否 | 创建时间 |
| `updated_at` | TEXT | 否 | 更新时间（覆盖设置时刷新） |

### 4.3 DDL

```sql
CREATE TABLE IF NOT EXISTS budgets (
    month      TEXT    NOT NULL PRIMARY KEY,
    amount     INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', '+8 hours')),
    CONSTRAINT ck_budgets_amount CHECK (amount > 0 AND amount <= 9999999999),
    CONSTRAINT ck_budgets_month  CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]')
);
```

### 4.4 升级说明

- 只新增表，**不修改** `categories` / `transactions` 的任何字段、索引或约束。
- 应用启动时自动建表；也可单独执行 `backend/sql/optional_features.sql`。
- 回退方式：`DROP TABLE budgets;` 并移除相关代码即可，不影响历史账单。

---

## 5. 预置数据（13 条分类）

| id | name | type |
| --- | --- | --- |
| 1 | 工资 | income |
| 2 | 奖金 | income |
| 3 | 兼职 | income |
| 4 | 投资收益 | income |
| 5 | 其他收入 | income |
| 6 | 餐饮 | expense |
| 7 | 交通 | expense |
| 8 | 购物 | expense |
| 9 | 居住 | expense |
| 10 | 娱乐 | expense |
| 11 | 医疗 | expense |
| 12 | 学习 | expense |
| 13 | 其他支出 | expense |

写入策略：仅当 `categories` 为空时插入，幂等，不覆盖用户数据。

```sql
INSERT INTO categories (id, name, type) VALUES
  (1,'工资','income'), (2,'奖金','income'), (3,'兼职','income'),
  (4,'投资收益','income'), (5,'其他收入','income'),
  (6,'餐饮','expense'), (7,'交通','expense'), (8,'购物','expense'),
  (9,'居住','expense'), (10,'娱乐','expense'), (11,'医疗','expense'),
  (12,'学习','expense'), (13,'其他支出','expense');
```

---

## 6. 关键口径

### 6.1 金额（元 ↔ 分）

| 层 | 单位 | 规则 |
| --- | --- | --- |
| 数据库 | 分（INTEGER） | 避免浮点误差 |
| API | 元（number，2 位小数） | 入库 `ROUND_HALF_UP` 转分，出库除以 100 |
| 上限 | 99,999,999.99 元 | = 9,999,999,999 分 |

### 6.2 月份与日期

- 业务日期只存 `YYYY-MM-DD`，字典序等于时间序。
- 月度区间：`[当月首日, 次月首日)`，跨年正确（2026-12 → 2027-01）。
- 月份归属以业务日期 `date` 为准，不使用创建时间。
- 业务日期上限为 `Asia/Shanghai` 的今天。

### 6.3 约束分工

| 约束 | 数据库 | 应用层 |
| --- | --- | --- |
| 金额范围/精度 | CHECK 范围 | 精度、类型、上限文案 |
| 日期格式/下界 | CHECK | 上限（今天） |
| 类型枚举 | CHECK | 与分类类型一致（1006） |
| 分类存在性 | 外键 | 提前返回 1007 |
| 删除被引用分类 | `ON DELETE RESTRICT` | 先计数返回 1010 |
| 分类重名 | 唯一索引 | 提前返回 1009 |

---

## 7. 常用运维 SQL

```sql
-- 当前数据量
SELECT (SELECT COUNT(*) FROM categories)   AS categories,
       (SELECT COUNT(*) FROM transactions) AS transactions,
       (SELECT COUNT(*) FROM budgets)      AS budgets;

-- 指定月份账单
SELECT id, amount, type, category_id, date, note
FROM transactions
WHERE date >= '2026-10-01' AND date < '2026-11-01'
ORDER BY date DESC, id DESC;

-- 关键词搜索（等价接口 keyword）
SELECT * FROM transactions
WHERE note LIKE '%地铁%'
ORDER BY date DESC, id DESC;

-- 查看预算
SELECT month, amount / 100.0 AS amount_yuan, updated_at
FROM budgets ORDER BY month DESC;

-- 某分类被引用条数
SELECT COUNT(*) FROM transactions WHERE category_id = 6;
```

**备份 / 恢复**

```bash
cp backend/ledger.db backend/ledger.db.bak-$(date +%Y%m%d)
cp backend/ledger.db.bak-20261021 backend/ledger.db
```

建议备份前停止写入（停服务或使用 `sqlite3 ledger.db ".backup backup.db"`）。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v1.0 | 2026-10-05 | MVP 三表：categories、transactions；预置 13 分类 |
| v1.1 | 2026-10-21 | 新增 budgets 表（选做功能 1）；原表结构与索引不变 |

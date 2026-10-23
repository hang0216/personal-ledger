# 选做功能使用说明（预算提醒 / 账单搜索 / 数据导出）

> 适用版本：在现有 Web MVP 基础上新增 3 个选做功能，原有账单管理、分类管理、月度报表功能保持不变。

## 1. 功能概览

| 功能 | 入口 | 数据库变更 |
| --- | --- | --- |
| 预算提醒 | 数据看板页顶部「预算条」 | 新增 `budgets` 表 |
| 账单搜索 | 账单管理页「搜索」区域 | 无（复用 `transactions`） |
| 数据导出 | 账单管理页「导出 CSV」按钮 | 无（纯前端导出） |

数据库脚本见 [optional_features.sql](../backend/sql/optional_features.sql)。

## 2. 启动方式（不变）

```bash
# 后端
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

应用启动时 `init_db()` 会自动创建 `budgets` 表（`CREATE TABLE IF NOT EXISTS` 语义），
已有数据库无需手工迁移；也可手动执行 `backend/sql/optional_features.sql`。

## 3. 预算提醒

**设置预算**

1. 进入「数据看板」，顶部预算条显示「本月预算 / 未设置」。
2. 点击「设置预算」，在弹窗输入金额（元，> 0，最多 2 位小数，上限 99,999,999.99）。
3. 保存后预算条显示预算金额、本月已支出、使用率进度条；再次点击可「修改预算」。

**超支提醒**

- 本月支出 **大于** 预算时，进入/刷新看板会弹出「预算超支提醒」弹窗，显示支出、预算与超支金额。
- 同一月份在一次页面会话中只提醒一次，避免反复打扰。
- 预算按月份独立保存，切换月份会加载该月自己的预算。

**校验与异常**

- 金额为空、非正数、超过上限：前端拦截并提示，不发起请求。
- 后端复用账单金额校验规则：非法金额返回 1002，超上限返回 1003，月份格式错误返回 1005。
- 预算加载失败不影响报表正常展示（预算区域显示「未设置」）。

**接口**

```
GET /api/budgets?month=2026-10     # 未设置时 data.amount = null
PUT /api/budgets  {"month":"2026-10","amount":3000}
-> {"code":0,"message":"OK","data":{"month":"2026-10","amount":3000.0}}
```

## 4. 账单搜索

「账单管理」页第二行为搜索区，支持：

- **日期范围**：选择开始 / 结束日期，可只填一端；范围限定 `2000-01-01 ~ 今天`。
- **收支类型**：沿用上方「类型」下拉（全部 / 收入 / 支出）。
- **收支分类**：沿用上方「分类」下拉。
- **备注关键词**：模糊匹配备注，去首尾空格，最长 100 字。

操作要点：

- 填写条件后点击「查询」或输入框内回车才发起请求，避免每次按键都请求。
- 提供日期或关键词即进入**搜索模式**：跨月查询，月份选择不生效（页面有提示）；
  点「清除搜索」回到当前月份视图。
- 结果仍按 `日期倒序 + id 倒序` 展示，底部显示「共 N 条记录」。

**校验与异常**

- 开始日期晚于结束日期：前端提示并阻止查询；直接调接口返回 1004「日期范围不合法」。
- 日期格式非法 / 超出范围：1004；关键词超过 100 字：1001「关键词长度超限」。
- 无匹配结果：返回空数组，列表显示「没有符合条件的记录」。
- 关键词中的 `%`、`_` 按普通字符匹配，不会被当作 SQL 通配符。

**接口（在原列表接口上扩展可选参数）**

```
GET /api/transactions?start_date=2026-01-01&end_date=2026-03-31&keyword=午餐
GET /api/transactions?keyword=地铁&type=expense&category_id=7
```

提供 `start_date` / `end_date` / `keyword` 任一参数即为搜索模式，`month` 被忽略。

## 5. 数据导出

1. 在账单管理页先按月份或搜索结果筛选出想要的记录。
2. 点击「导出 CSV」，浏览器直接下载 `账单_YYYY-MM-DD.csv`。
3. 导出内容为**当前列表所见记录**，列为：日期、类型、分类、金额(元)、备注。

细节：

- 文件为 UTF-8 **带 BOM** + CRLF 换行，Excel 双击打开中文不乱码、不串列。
- 备注中的逗号、引号、换行会按 CSV 规范转义。
- 列表为空时按钮禁用；直接调用会提示「当前没有可导出的记录」。
- 导出完全在前端完成，不新增后端接口，也不写数据库。

## 6. 改动清单（便于评审）

后端：

- 新增 `app/models/budget.py`、`app/schemas/budget.py`、`app/services/budget_service.py`、`app/routers/budgets.py`
- `app/database/init_db.py`：注册 `Budget` 模型并建表
- `app/main.py`：注册预算路由
- `app/core/validators.py`：新增 `validate_date_range`、`validate_keyword`
- `app/schemas/transaction.py`、`app/services/transaction_service.py`、`app/routers/transactions.py`：列表接口扩展搜索参数
- 新增 `sql/optional_features.sql`

前端：

- 新增 `src/api/budgets.js`、`src/utils/csv.js`
- `src/api/transactions.js`：支持 `startDate / endDate / keyword`
- `src/views/DashboardView.vue`：预算条、预算设置弹窗、超支提醒
- `src/components/TransactionFilterBar.vue`：搜索区与导出按钮
- `src/views/TransactionsView.vue`：搜索状态、查询/清除/重置、CSV 导出

原有接口路径、请求/响应结构、错误码与页面风格均保持兼容，未修改 `categories` / `transactions` 表结构。

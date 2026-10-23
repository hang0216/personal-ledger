# 个人记账本 — 技术架构设计（architecture.md）

| 项目名称 | 个人记账本（Personal Ledger） |
| --- | --- |
| 版本 | v1.0 (MVP) |
| 文档类型 | 技术架构设计文档 |
| 依据 | `spec.md` v1.1 |
| 前端 | Vue 3 + Vite + Element Plus + Chart.js |
| 后端 | Python + FastAPI |
| 数据库 | SQLite |

> 本文档严格依据 `spec.md` v1.1 编写，不新增业务功能、不修改 spec。所有架构决策以"MVP 优先、结构清晰、易理解、易调试、易测试、适合课程项目"为准，不引入非必要复杂技术。

---

## 1. 总体系统架构

采用**前后端分离的单体应用**（Monolith，但前后端物理分离），后端为唯一的业务与数据入口。

```
┌────────────────────────────────────────────────────────────┐
│                        浏览器 (SPA)                         │
│   Vue 3 + Vite + Element Plus + Chart.js                    │
│   ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│   │  views   │→ │  components  │  │  api (axios 封装)   │   │
│   └──────────┘  └──────────────┘  └──────────┬──────────┘   │
│                                     router/index.js          │
└───────────────────────────────────────┬────────────────────┘
                                        │ HTTP / JSON
                                        │ (统一结构 code/message/data)
┌───────────────────────────────────────▼────────────────────┐
│                    FastAPI 后端 (uvicorn)                   │
│   routers/  →  schemas/  →  services/  →  models/           │
│        │                        │            │              │
│        │                        │            ▼              │
│        │                        │        database/          │
│        └── core/ (错误码 / 统一响应 / 统一校验 / 时区 / 金额) │
└───────────────────────────────────────┬────────────────────┘
                                        │ SQLAlchemy Session
                                        ▼
                              ┌───────────────────┐
                              │  SQLite 单文件库   │
                              │  ledger.db        │
                              │  categories       │
                              │  transactions     │
                              └───────────────────┘
```

**核心特征**
- 单一后端进程，无微服务、无消息队列、无缓存中间件（Redis 等）。
- 数据库为本地 SQLite 单文件，无独立数据库服务。
- 无认证与权限层：所有接口为单用户本地访问（对应 spec §3.1）。

---

## 2. 前后端关系

| 维度 | 约定 |
| --- | --- |
| 通信协议 | HTTP + JSON |
| 接口前缀 | 统一 `/api`，例如 `/api/transactions` |
| 职责边界 | 前端只做展示、交互与**形式校验**；后端做**全部业务规则与数据校验**（前端校验仅提升体验，不作为安全边界） |
| 数据契约 | 统一响应结构 `{ code, message, data }`，见 spec §6.2 |
| 金额语义 | 接口层金额一律为「元」（最多 2 位小数）；「分」的存储细节对前端完全透明（spec §7.7） |
| 时间语义 | 后端以业务时区 `Asia/Shanghai` 判断"今天 / 当前月"（spec §6.2、§8）；前端不参与日期合法性判等 |
| 无状态 | 后端不保存会话；前端不发 Cookie，不使用 credentials |
| 错误约定 | 前端不解释 HTTP 状态码细节，统一读取响应体 `code` 与 `message` |

**接口清单**（完全对应 spec §6.1，不增不减）

| 方法 | 路径 | 归属 router |
| --- | --- | --- |
| GET | `/api/categories` | categories |
| POST | `/api/categories` | categories |
| DELETE | `/api/categories/{id}` | categories |
| GET | `/api/transactions` | transactions |
| POST | `/api/transactions` | transactions |
| PUT | `/api/transactions/{id}` | transactions |
| DELETE | `/api/transactions/{id}` | transactions |
| GET | `/api/reports/monthly` | reports |

---

## 3. 前后端数据流

### 3.1 读数据流（以账单列表为例）

```
TransactionListView
  → api/transactions.js#listTransactions(month)
  → axios 实例（api/request.js：baseURL、超时、拦截器）
  → GET /api/transactions?month=2026-10
  → routers/transactions.py（解析 query 参数）
  → schemas（参数模型校验 month 格式）
  → services/transaction_service.py#list_transactions()
       ├─ 计算月份区间（date 归属，跨年安全）
       └─ 通过 models 查询 SQLite（排序 date DESC, id DESC）
  → service 将 amount 由「分」转「元」
  → router 组装 { code:0, message:"success", data:[...] }
  → 前端响应拦截器解包 data
  → View 绑定到 Element Plus 表格渲染
```

### 3.2 写数据流（以新增账单为例）

```
TransactionFormDialog（用户填写）
  → 前端形式校验（必填 / 金额格式 / 日期范围）
  → 提交期间禁用"保存"按钮（spec §7.1、E-16）
  → POST /api/transactions（金额单位为元）
  → routers → schemas（Pydantic 结构校验）
  → services/transaction_service.py#create_transaction()
       ├─ 调用 core/validators 统一校验（金额 / 日期 / 分类存在且类型一致）
       ├─ 金额「元 → 分」×100 取整
       └─ 事务写入 SQLite
  → 返回新记录（金额「分 → 元」）
  → 前端刷新列表 + 成功提示
```

### 3.3 报表数据流（特殊：计算集中在后端）

```
ReportView（月份切换）
  → GET /api/reports/monthly?month=2026-10
  → services/report_service.py#build_monthly_report()
       ├─ 月份区间 [当月首日, 次月首日)
       ├─ SUM 收入 / SUM 支出（整数分）
       ├─ balance = income - expense（可为负）
       ├─ 支出 GROUP BY category_id → 各组整数分金额
       ├─ percentage = 组金额 / 总支出 × 100（后端唯一计算，2 位小数）
       └─ 全部 ÷100 转「元」
  → { total_income, total_expense, balance, expense_by_category[] }
  → Chart.js 直接使用后端 percentage 绘制饼图（不在前端重算，spec §6.3 R-21）
```

**关键数据流原则**
1. 业务规则只存在于后端 service，前端不复制业务判断（避免双份口径）。
2. 金额的「分/元」转换只发生在**后端边界**：入站（schema → service）与出站（service → schema），中间计算始终为分。
3. 前端所有请求经统一 axios 实例，异常出口唯一。

---

## 4. 前端模块划分

| 层 | 目录 | 职责 | 不做什么 |
| --- | --- | --- | --- |
| 入口 | `src/main.js`、`src/App.vue` | 创建应用、挂载 Element Plus、挂载路由 | 不写业务逻辑 |
| 路由 | `src/router/` | 页面路由 `/`、`/categories`、`/reports` | 不写数据请求 |
| 视图 | `src/views/` | 页面级编排：取数、组装组件、处理空状态 | 不直接调 axios 细节 |
| 组件 | `src/components/` | 可复用 UI：表单弹窗、表格、月份选择、汇总卡片、饼图 | 不直接访问全局状态 |
| API | `src/api/` | axios 实例 + 各领域接口函数 | 不写业务规则 |
| 工具 | `src/utils/` | 金额格式化（`¥1,234.56` / `-¥200.00`）、月份/日期工具 | 不做业务校验的唯一来源 |

**视图与组件**

| 文件 | 对应 spec 页面 | 要点 |
| --- | --- | --- |
| `views/TransactionListView.vue` | 记录列表 `/` | 月份切换；`date DESC, id DESC` 由后端保证；增删改入口 |
| `views/CategoryListView.vue` | 分类管理 `/categories` | 收入/支出分组；新增、删除（二次确认） |
| `views/ReportView.vue` | 月度报表 `/reports` | 三项汇总卡片 + 饼图 + 分类明细；两种空状态 |
| `components/TransactionFormDialog.vue` | 新增/编辑弹窗 | 类型-分类联动；POST/PUT 复用；提交禁用按钮 |
| `components/CategorySelect.vue` | — | 按类型过滤分类下拉框 |
| `components/MonthPicker.vue` | — | `YYYY-MM` 选择，默认当前月 |
| `components/SummaryCards.vue` | — | 收入/支出/结余卡片，负结余格式化 |
| `components/ExpensePieChart.vue` | — | Chart.js 饼图，直接消费后端 `percentage` |

**状态管理**：MVP 不引入 Pinia / Vuex。页面数据在各自 View 内维护，跨页共享需求不存在（无登录、无全局用户态），避免非必要复杂度。

**API 模块**

| 文件 | 职责 |
| --- | --- |
| `api/request.js` | 创建 axios 实例；请求拦截器；响应拦截器统一解包 `data`、统一抛错（对应 spec E-15） |
| `api/categories.js` | `listCategories(type?)`、`createCategory(body)`、`deleteCategory(id)` |
| `api/transactions.js` | `listTransactions(params)`、`createTransaction(body)`、`updateTransaction(id, body)`、`deleteTransaction(id)` |
| `api/reports.js` | `getMonthlyReport(month)` |

---

## 5. 后端模块划分

| 层 | 目录 | 职责 | 依赖 |
| --- | --- | --- | --- |
| 应用入口 | `app/main.py` | 创建 FastAPI 实例；注册 CORS、异常处理器、路由；启动时初始化数据库 | routers, core, database |
| 路由层 | `app/routers/` | 解析 HTTP 参数、调用 service、返回统一响应；不含业务规则 | schemas, services, core |
| 数据契约层 | `app/schemas/` | Pydantic 请求/响应模型；字段级结构校验与序列化 | 无（纯定义） |
| 业务层 | `app/services/` | 全部业务规则、统一校验编排、金额分/元转换、事务 | models, core, schemas |
| 数据模型层 | `app/models/` | SQLAlchemy ORM 实体与表映射 | database |
| 数据库层 | `app/database/` | 引擎、会话、建表、初始化种子、连接配置 | — |
| 核心支撑 | `app/core/` | 错误码、业务异常、统一响应、统一校验函数、时区、金额工具、配置 | 无 |

**routers**

| 文件 | 覆盖接口 | 说明 |
| --- | --- | --- |
| `routers/categories.py` | 分类 3 个接口 | type 过滤、去重冲突与"有引用拒绝删除"错误映射 |
| `routers/transactions.py` | 账单 4 个接口 | 列表筛选、排序由 service 保证 |
| `routers/reports.py` | 报表 1 个接口 | 仅一个只读聚合接口 |

**services**

| 文件 | 职责 |
| --- | --- |
| `services/category_service.py` | 分类查询/新增/删除；名称去空格与唯一性检查；删除前引用计数；`IntegrityError` 与 RESTRICT 的错误映射 |
| `services/transaction_service.py` | 账单 CRUD；调用统一校验；金额元→分；列表按 `date DESC, id DESC` |
| `services/report_service.py` | 月份区间计算、聚合、占比计算、空数据兜底 |

**schemas**

| 文件 | 模型（示意，非代码） |
| --- | --- |
| `schemas/category.py` | `CategoryCreate`、`CategoryOut` |
| `schemas/transaction.py` | `TransactionCreate`、`TransactionUpdate`（字段与 Create 完全一致）、`TransactionOut`、`TransactionQuery` |
| `schemas/report.py` | `MonthlyReportOut`、`CategoryExpenseItem` |
| `schemas/common.py` | 统一响应包装 `ApiResponse[T]` |

> 设计要点：`TransactionUpdate` 与 `TransactionCreate` 字段与校验**完全一致**（spec §5.1 R-14 / AC-24），实现上可共用一个基类，保证 PUT 与 POST 行为同源。

**core**

| 文件 | 职责 |
| --- | --- |
| `core/errors.py` | 错误码常量（1001–1010、1999）与 `AppError(code, http_status, message)` |
| `core/response.py` | `ok(data)` / `fail(...)` 统一 `{code,message,data}` 组装 |
| `core/exceptions.py` | 全局异常处理器：`RequestValidationError`、`AppError`、`HTTPException`、兜底 `Exception` |
| `core/validators.py` | **统一业务校验函数**：金额、日期、月份、分类存在性与类型一致性 |
| `core/money.py` | `yuan_to_cents()` / `cents_to_yuan()`（唯一转换入口） |
| `core/timeutil.py` | 业务时区常量、`today()`、`current_month()`、`month_range(month)`（含跨年） |
| `core/config.py` | 数据库路径、CORS 允许源、金额上限、日期下界等常量 |

> `core/validators.py`、`core/money.py`、`core/timeutil.py` 是 spec §11"可测试性"要求的**可独立单元测试的纯函数**所在地，不依赖数据库与 HTTP。

---

## 6. 数据库模块

| 项 | 设计 |
| --- | --- |
| 引擎 | SQLite 单文件 `ledger.db`，随项目存放（spec §8） |
| 访问方式 | SQLAlchemy ORM + Session，按请求提供会话 |
| 建表 | 启动时 `create_all` + 初始化种子（幂等，仅在表为空时插入预置分类） |
| 事务 | 写操作（新增/编辑/删除）在单个事务内提交，失败回滚（spec §11 可靠性） |
| 外键 | **必须启用 `PRAGMA foreign_keys = ON`**，否则 SQLite 默认忽略外键，`ON DELETE RESTRICT` 不会生效——这是"无孤儿账单"（spec §7.5 R-18）能否成立的前提 |
| 索引 | `categories(name, type)` 唯一索引；`transactions(date)`、`transactions(category_id)`、`transactions(type)` 普通索引 |
| 金额 | `transactions.amount` 为 INTEGER（分）；上限 99,999,999.99 元 = 9,999,999,999 分，在 64 位整型范围内 |
| 时间 | `created_at` / `updated_at` 按业务时区 `Asia/Shanghai` 生成 |

**表结构**（与 spec §4 完全一致，此处仅描述模块归属，DDL 留待数据库设计阶段）

- `categories`：`id`、`name`、`type`、`created_at`；唯一约束 `(name, type)`；**无 `is_default`**（spec R-15）。
- `transactions`：`id`、`amount`(INTEGER 分)、`type`、`category_id`(FK, RESTRICT)、`date`、`note`、`created_at`、`updated_at`。

**文件划分**

| 文件 | 职责 |
| --- | --- |
| `database/engine.py` | 引擎、连接参数、`PRAGMA foreign_keys=ON` |
| `database/session.py` | Session 工厂与依赖注入函数 |
| `database/init_db.py` | 建表、种子数据（收入 5 类 / 支出 8 类）、幂等初始化 |
| `database/base.py` | ORM 声明式基类 |

---

## 7. API 层

### 7.1 分层职责

```
请求 → routers（HTTP 语义）
        ├─ 参数解析（path / query / body）
        ├─ schemas 结构校验（类型、必填、格式）
        ├─ 调用 service（业务）
        └─ core.response 组装统一结构
      → services（业务语义，唯一业务入口）
```

- router **不写** if/else 业务规则，只做转发与响应包装。
- service **不感知** HTTP，只接受已验证的数据、返回领域结果。
- 因此同样业务可从 pytest 直接调用 service 测试，无需起 HTTP 服务（spec §11 可测试性）。

### 7.2 响应与状态码

- 成功：`{ code: 0, message: "success", data: ... }`，HTTP 200。
- 业务失败：`{ code: 1xxx, message: "...", data: null }`，HTTP 与错误码表一致（400 / 404 / 409）。

错误码归属（spec §6.2 / §9）：

| code | HTTP | 触发层 |
| --- | --- | --- |
| 1001 | 400 | schemas 校验 / 全局 `RequestValidationError` 处理器 / 备注、分类名长度 |
| 1002、1003 | 400 | core.validators 金额规则 |
| 1004 | 400 | core.validators 日期规则 |
| 1005 | 400 | core.validators 月份规则 |
| 1006 | 400 | transaction_service 分类类型一致性 |
| 1007 | 404 | transaction_service 分类存在性 |
| 1008 | 404 | transaction_service 记录存在性 |
| 1009 | 409 | category_service 重名（预检查 + 唯一索引兜底） |
| 1010 | 409 | category_service 引用计数 + DB RESTRICT 兜底 |
| 1999 | 500 | core.exceptions 兜底处理器 |

### 7.3 接口契约要点

| 接口 | 入参校验 | 业务校验 | 默认行为 |
| --- | --- | --- | --- |
| `GET /api/categories` | `type` 可选枚举 | — | 按 type 分组返回（支出/收入） |
| `POST /api/categories` | name 1–20、type 枚举 | 去空格、同类型重名 | — |
| `DELETE /api/categories/{id}` | id 整数 | 存在性 + 引用计数 + RESTRICT | — |
| `GET /api/transactions` | `month` 可选、`type` 可选、`category_id` 可选 | 月份区间 | `month` 缺省 = 当前月；排序 `date DESC, id DESC` |
| `POST /api/transactions` | 统一模型（元） | 统一校验 + 元→分 | — |
| `PUT /api/transactions/{id}` | 与 POST 完全一致 | 与 POST 完全一致 + 记录存在性 | 全量覆盖，更新 `updated_at` |
| `DELETE /api/transactions/{id}` | id 整数 | 记录存在性 | — |
| `GET /api/reports/monthly` | `month` 可选 | 月份区间（跨年安全） | `month` 缺省 = 当前月 |

> Swagger：由 FastAPI 自动生成，`ApiResponse[T]` 作为 `response_model`，满足 spec AC-16。

---

## 8. 月度报表模块

独立为 `services/report_service.py`，是 MVP 中唯一"计算型"模块，全部逻辑集中在后端。

| 步骤 | 规则 | spec 依据 |
| --- | --- | --- |
| 1. 月份解析 | `YYYY-MM`，缺省 = 业务时区当前月 | §5.3、§7.6 |
| 2. 区间计算 | `[当月首日 00:00, 次月首日 00:00)`；按自然月进位，`2026-12 → 2027-01-01` | §7.6 R-05 |
| 3. 归属字段 | 一律按业务日期 `date`，与 `created_at/updated_at` 无关 | §7.6 R-03 |
| 4. 收入汇总 | 区间内 `type=income` 的 amount（分）求和，默认 0 | §7.6 |
| 5. 支出汇总 | 区间内 `type=expense` 的 amount（分）求和，默认 0 | §7.6 |
| 6. 结余 | `balance = income - expense`，**允许为负** | §7.6 R-22 |
| 7. 分类占比 | 按 `category_id` 分组求和；`percentage = 组金额 / 总支出 × 100`，保留 2 位小数，按金额降序 | §6.3 R-10、R-21 |
| 8. 精度 | 全程整数分计算，仅出口 ÷100 转元 | §7.7 |
| 9. 空数据 | 总支出为 0 → `expense_by_category = []`；无任何记录 → 各总额为 0 | §6.3、E-13 |

**空状态在前端呈现**（spec §7.8 R-11）：

| 后端返回特征 | 前端表现 |
| --- | --- |
| 收入=0 且 支出=0 | 卡片均显示 `¥0.00`；饼图区显示"本月暂无数据" |
| 收入>0 且 支出=0 | 饼图区显示"本月暂无支出数据" |
| 支出>0 | 正常饼图，直接使用后端 `percentage` |

**报表模块的边界**
- 只读，无写操作；不产生缓存、不落报表快照表（MVP 不引入冗余存储）。
- 不提供收入分类占比（spec 仅要求支出占比，不扩展）。

---

## 9. 错误处理

采用**三层统一错误处理**，出口唯一。

```
① schemas / Pydantic  → RequestValidationError 处理器 → 1001 / 400
② core.validators / services → 抛 AppError(code, http) → AppError 处理器 → 对应 code/HTTP
③ 未预期异常 → 兜底 Exception 处理器 → 1999 / 500（记录日志，不返回堆栈）
```

| 机制 | 说明 |
| --- | --- |
| `AppError` | 业务异常的唯一载体，携带 code / http_status / message；由 `core.exceptions` 统一转为 `{code,message,data:null}` |
| `RequestValidationError` | 覆盖 spec E-03；将 FastAPI 默认 422 统一转换为 `1001 / 400` |
| 兜底处理器 | 覆盖 spec E-14；避免堆栈泄露（spec §11 可靠性） |
| 数据库异常映射 | `IntegrityError`（唯一约束）→ `1009 / 409`；外键 RESTRICT 冲突 → `1010 / 409` |
| service 不吞异常 | service 只抛 `AppError` 或让异常上抛，由全局处理器统一转换，杜绝各处自定义响应格式 |
| 前端错误出口 | `api/request.js` 响应拦截器统一捕获：业务错误读 `message` 弹 Element Plus 提示；网络/超时归入 spec E-15 |
| 前端静默降级 | 错误不破坏页面结构，不产生未捕获 Promise 异常（spec AC-15） |

**错误文案来源**：统一维护在 `core/errors.py`（code → 默认 message），与 spec §9 的文案一致，避免散落各处。

---

## 10. 数据校验

**双层校验模型**

| 层 | 位置 | 内容 | 失败结果 |
| --- | --- | --- | --- |
| 结构校验 | `schemas/`（Pydantic） | 类型、必填、枚举、字符串长度、格式 | `1001 / 400`（经全局处理器） |
| 业务校验 | `core/validators.py` | 金额数值区间与小数位、日期上下界与时区、月份格式与范围、分类存在性与类型一致性 | 1002–1007 |

**统一校验函数**（spec §5.1 R-14 / AC-24）

| 校验项 | 规则 | 错误码 |
| --- | --- | --- |
| 金额 | 合法数字；`> 0`；`≤ 99,999,999.99` 元；最多 2 位小数 | 1002 / 1003 |
| 日期 | 严格 `YYYY-MM-DD`（补零）；`≥ 2000-01-01`；`≤` 业务时区今天 | 1004 |
| 月份 | 严格 `YYYY-MM`，月份 `01–12` | 1005 |
| 分类存在性 | `category_id` 必须存在（含未被删除） | 1007 |
| 分类类型一致性 | `category.type == payload.type` | 1006 |
| 分类名称 | 去首尾空格后 1–20 个 Unicode 字符（按码点计，emoji 计 1）；同类型唯一 | 1001 / 1009 |
| 备注 | ≤ 100 个 Unicode 字符 | 1001 |

**强制约定**
1. `POST` 与 `PUT` **调用同一个校验函数**，保证 AC-24（同输入同错误码）。
2. 前端校验仅为用户体验（即时反馈），后端校验为唯一可信来源。
3. 长度一律按 Unicode 码点计数（`len(str)`），emoji 计 1（spec §5.1 R-24）。
4. 金额转换只有一个入口 `core/money.py`，禁止在 router 或 model 内散落 ×100 / ÷100。

---

## 11. CORS 和开发环境访问方式

**开发环境（默认）**

| 项 | 配置 |
| --- | --- |
| 后端 | `uvicorn app.main:app --reload`，监听 `http://127.0.0.1:8000` |
| 前端 | `vite`，监听 `http://localhost:5173` |
| 跨域 | 启用 `CORSMiddleware`，`allow_origins=["http://localhost:5173"]`，`allow_methods=["*"]`，`allow_headers=["*"]`，`allow_credentials=False`（无认证，无需凭证） |
| 可选优化 | Vite `server.proxy` 将 `/api` 代理到 `:8000`，使开发期同源；代理与 CORS 二者任一即可，MVP 默认按 spec §8 启用 CORS |
| 前端 baseURL | `api/request.js` 中为 `/api`（配合代理）或 `http://127.0.0.1:8000/api`（直连 + CORS） |

**生产 / 演示环境**

| 项 | 配置 |
| --- | --- |
| 前端 | `vite build` 产出静态文件 |
| 后端 | FastAPI 挂载 `StaticFiles` 托管前端产物，前后端**同源**，不开放跨域（spec §8） |
| 启动 | 单条命令启动后端即同时提供页面与 API |

> 底线要求：开发环境不得因 CORS 阻塞联调（spec §8 约束）；生产环境不保留宽泛 CORS。

---

## 12. 项目目录结构

```
personal-ledger/
├── spec.md
├── docs/
│   └── architecture.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 实例、中间件、路由注册、启动初始化
│   │   ├── core/
│   │   │   ├── config.py           # 常量：DB 路径、CORS 源、金额上限、日期下界
│   │   │   ├── errors.py           # 错误码常量与文案
│   │   │   ├── exceptions.py       # 全局异常处理器
│   │   │   ├── response.py         # 统一响应组装
│   │   │   ├── validators.py       # 统一业务校验函数
│   │   │   ├── money.py            # 元/分转换（唯一入口）
│   │   │   └── timeutil.py         # 业务时区、今天、当前月、月份区间
│   │   ├── database/
│   │   │   ├── base.py             # ORM 声明式基类
│   │   │   ├── engine.py           # 引擎 + PRAGMA foreign_keys=ON
│   │   │   ├── session.py          # Session 工厂与依赖
│   │   │   └── init_db.py          # 建表 + 预置分类种子（幂等）
│   │   ├── models/
│   │   │   ├── category.py
│   │   │   └── transaction.py
│   │   ├── schemas/
│   │   │   ├── common.py           # ApiResponse[T]
│   │   │   ├── category.py
│   │   │   ├── transaction.py      # Create / Update 共用字段定义
│   │   │   └── report.py
│   │   ├── services/
│   │   │   ├── category_service.py
│   │   │   ├── transaction_service.py
│   │   │   └── report_service.py
│   │   └── routers/
│   │       ├── categories.py
│   │       ├── transactions.py
│   │       └── reports.py
│   ├── tests/                      # 单元测试（service / core 纯函数优先）
│   ├── requirements.txt
│   └── ledger.db                   # 运行时生成（不提交）
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js              # 可选 server.proxy
    └── src/
        ├── main.js
        ├── App.vue
        ├── router/
        │   └── index.js
        ├── api/
        │   ├── request.js          # axios 实例 + 拦截器
        │   ├── categories.js
        │   ├── transactions.js
        │   └── reports.js
        ├── views/
        │   ├── TransactionListView.vue
        │   ├── CategoryListView.vue
        │   └── ReportView.vue
        ├── components/
        │   ├── TransactionFormDialog.vue
        │   ├── CategorySelect.vue
        │   ├── MonthPicker.vue
        │   ├── SummaryCards.vue
        │   └── ExpensePieChart.vue
        └── utils/
            ├── format.js           # ¥1,234.56 / -¥200.00
            └── date.js             # YYYY-MM / YYYY-MM-DD 辅助
```

> 目录仅命名与分工，不含业务代码；具体实现留待后续阶段。

---

## 13. 模块之间的依赖关系

### 13.1 后端依赖方向（严格单向，无循环）

```
main.py
  ├── core.config
  ├── core.exceptions
  ├── database.init_db ──→ database.engine ──→ database.base
  └── routers/* ──→ schemas/* ──→ (无依赖)
        │
        └── services/* ──→ models/* ──→ database.base
                 │
                 └── core.{validators, money, timeutil, errors}
```

| 模块 | 允许依赖 | 禁止依赖 |
| --- | --- | --- |
| `routers` | schemas、services、core.response/exceptions | 禁止直接访问 models / database |
| `services` | models、core、database.session | 禁止 import fastapi / HTTPException |
| `schemas` | 仅标准库与 Pydantic | 禁止依赖任何内部模块 |
| `models` | database.base | 禁止依赖 services / routers |
| `database` | core.config | 禁止依赖上层业务 |
| `core` | 仅标准库 | 禁止依赖任何上层模块 |

> 约束意义：service 不依赖 HTTP → 可脱离 Web 层单测；router 不碰 ORM → 便于后续替换数据访问方式而不动接口逻辑。

### 13.2 前端依赖方向

```
main.js → App.vue → router/index.js → views/*
                                        ├── components/*
                                        ├── api/* → request.js (axios)
                                        └── utils/*
```

| 模块 | 允许依赖 | 禁止依赖 |
| --- | --- | --- |
| `views` | components、api、utils | 禁止绕过 api 直接写 axios 调用 |
| `components` | utils | 禁止直接发请求（数据经 props/emit 与 view 交互） |
| `api` | request.js | 禁止引用 views / components |
| `utils` | 仅标准库 | 禁止依赖 Vue 组件 |

### 13.3 跨层关键依赖（验收相关）

| 能力 | 唯一实现位置 | 被谁消费 |
| --- | --- | --- |
| 元/分转换 | `core/money.py` | transaction_service、report_service |
| 统一业务校验 | `core/validators.py` | transaction_service（POST/PUT 共用）、category_service |
| 月份区间（跨年） | `core/timeutil.py` | transaction_service、report_service |
| 统一响应/错误码 | `core/response.py`、`core/errors.py` | 全部 routers 与 exceptions |
| 百分比计算 | report_service | 前端 `ExpensePieChart.vue`（不重算） |
| 金额格式化 | frontend `utils/format.js` | SummaryCards、交易表格、报表 |

---

## 14. MVP 范围与 Out of Scope

### 14.1 本版本范围（与 spec §3 一致，三大模块）

| 模块 | 覆盖能力 | 对应接口 |
| --- | --- | --- |
| 收支记录 | 新增、编辑、删除、按月份查看 | `/api/transactions` × 4 |
| 分类管理 | 查看（按收入/支出分组）、新增、删除（无引用时） | `/api/categories` × 3 |
| 月度报表 | 收入/支出/结余汇总 + 支出分类占比饼图 | `/api/reports/monthly` |

### 14.2 Out of Scope（架构层面同样不提供任何支撑设施）

- 用户登录 / 注册 / 多用户 → 无 auth 中间件、无用户表
- 支付 / 第三方账单 → 无外部支付集成
- 角色与复杂权限 → 无权限层
- Excel / CSV 导入导出 → 无导入导出端点
- 消息通知 / 提醒推送 → 无通知模块
- 第三方付费服务（云同步、AI 分析） → 无外部服务调用
- 多货币 / 汇率 → 仅人民币，无货币字段
- 预算告警 / 周期性账单 → 无定时任务、无调度器
- 分类编辑 / 重命名 → 分类仅新增与删除
- 后端幂等键 / 防重复提交 → 仅前端提交期间禁用按钮
- Redis / 消息队列 / 微服务 / Docker / 其他数据库 → 技术栈保持单体 + SQLite
- 移动端 App 打包 → 仅响应式 Web
- 记录搜索、分页、趋势图 → 列入 Backlog（spec §12），本期不实现

---

# 附录：评审结论

## 一、架构是否完整覆盖 spec.md

| spec 章节 | 覆盖位置 | 状态 |
| --- | --- | --- |
| §1 背景 / §2 用户故事 | §14.1、§1 | ✅ |
| §3 功能列表 / §3.1 Out of Scope | §14.1、§14.2、§4、§5 | ✅ |
| §4 数据模型（含分存储、RESTRICT、无 is_default） | §6、§5 | ✅ |
| §5 输入与校验规则 | §10、§7.3 | ✅ |
| §6.1 接口清单 | §2、§7.3 | ✅ |
| §6.2 统一响应 / 错误码 / 422 转换 | §7.2、§9 | ✅ |
| §6.3 报表结构 / percentage 唯一口径 | §8、§13.3 | ✅ |
| §6.4 前端页面 | §4 | ✅ |
| §7.1–§7.8 业务逻辑 | §3、§5、§7、§8、§9 | ✅ |
| §8 约束（时区、CORS、架构、图表） | §6、§10、§11 | ✅ |
| §9 异常 E-01–E-16 | §9、§7.2 | ✅ |
| §10 验收标准 AC-01–AC-24 | §13.3、§8、§10（可测试性落点） | ✅ |
| §11 非功能需求 | §6（事务/外键）、§9（不泄露堆栈）、§10/§13.3（可测试性）、§11（部署） | ✅ |
| §12 Backlog | §14.2 | ✅ |

**结论：spec.md 的全部模块与约束均已在架构中找到对应落点，覆盖完整。**

## 二、发现的需求冲突或遗漏

未发现与 spec 的**直接冲突**（所有决策均与 spec 一致）。以下为实现前需注意的**遗漏或需补充确认**项，均不影响本阶段推进：

| 编号 | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| G-01 | 遗漏（实现关键） | spec §7.5 依赖数据库层 `ON DELETE RESTRICT` 兜底，但 **SQLite 默认不启用外键**。 | 架构已强制 `PRAGMA foreign_keys = ON`（§6）；数据库设计阶段须落地，否则"无孤儿账单"不成立。 |
| G-02 | 表述歧义 | spec §6.1 说列表 `month` 参数"可选"，§6.1 注又说缺省回退当前月，未明确"列表是否真的允许不带 month 而返回全部"。 | 架构暂定：列表 `month` 缺省 = 当前月（与报表一致）；建议在数据库/API 阶段确认，或改文档为"必填/固定当前月"。 |
| G-03 | 遗漏 | spec 未定义 `GET /api/categories` 的**返回排序**。 | 架构暂定：按 `type` 再按 `id` 升序；建议补入 API 契约。 |
| G-04 | 遗漏 | spec 说名称"去首尾空格后比较"唯一，但未规定**入库是否存储去空格后的值**。 | 架构暂定：入库统一存去除首尾空格后的值；建议明确。 |
| G-05 | 遗漏 | spec 未规定 `created_at` / `updated_at` 的**存储格式与精度**（SQLite 无原生 DATETIME）。 | 建议数据库阶段统一为 `YYYY-MM-DD HH:MM:SS` 文本并按 `Asia/Shanghai` 写入。 |
| G-06 | 边界细节 | spec §6.3 允许某分类 `percentage` 四舍五入为 `0.00`（占比极小时），但未说明是否展示。 | 架构不特殊处理，直接展示；如需隐藏需在 API 阶段补充规则。 |
| G-07 | 遗漏 | spec 未定义重复删除同一分类（并发/连续点击）的二次响应。 | 统一按"分类不存在"返回 404（1007），与 E-12 语义一致。 |

## 三、是否建议进入数据库设计阶段

**建议进入。**

理由：
1. spec v1.1 已闭环（金额整数分、时区、月份区间、错误码、空状态），架构已将其全部映射到明确模块与依赖方向。
2. 唯一必须落实的实现关键点（G-01 `PRAGMA foreign_keys = ON`）已在架构中显式声明，数据库设计阶段可直接落地。
3. spec §4 的表结构与约束可直接转为 DDL，无需前置澄清。

**进入数据库设计阶段时需一并产出**
1. `categories` / `transactions` 的完整 DDL（含 `(name,type)` 唯一索引、`ON DELETE RESTRICT`、`date/category_id/type` 索引）。
2. 预置分类种子数据脚本（收入 5 类、支出 8 类）。
3. 外键启用与初始化幂等策略。
4. 同时确认附录 G-02、G-03、G-04、G-05 四项待定细节。

**建议顺序**：`spec.md` → `docs/architecture.md`（本文档）→ **数据库设计（DDL + 种子）** → API 契约 → 前端/后端实现。
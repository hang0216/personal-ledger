# 个人记账本 — API 设计（api-design.md）

| 项目名称 | 个人记账本（Personal Ledger） |
| --- | --- |
| 版本 | v1.1 (MVP) |
| 文档类型 | RESTful API 设计文档 |
| 依据 | `spec.md` v1.2、`docs/architecture.md` v1.0、`docs/database-design.md` v1.0 |
| 技术栈 | Python + FastAPI + SQLite |
| 端点总数 | 8 |

> v1.1 修订说明：依据四文档交叉审查结论修订。修复 R-01（金额类型拆分）、R-02（错误文案对齐 spec §9）、R-03（互斥筛选行为）、R-04（移除无依据的"存在 N 条"提示）、R-06（字符长度口径）、R-07（补 12 月跨年示例）、R-08（缺省值可复现）、R-17（单位标注）。端点数量与 MVP 范围不变。
> 本文档严格依据三份上游文档编写，冲突时以 `spec.md` 为最高优先级。

---

## 1. 总览

| # | 模块 | 方法 | 路径 | 功能 |
| --- | --- | --- | --- | --- |
| 1 | 收支记录 | GET | `/api/transactions` | 查询账单列表（按月/类型/分类筛选） |
| 2 | 收支记录 | POST | `/api/transactions` | 新增账单 |
| 3 | 收支记录 | PUT | `/api/transactions/{id}` | 编辑账单（全量覆盖） |
| 4 | 收支记录 | DELETE | `/api/transactions/{id}` | 删除账单 |
| 5 | 分类管理 | GET | `/api/categories` | 查询分类列表（可按类型筛选） |
| 6 | 分类管理 | POST | `/api/categories` | 新增分类 |
| 7 | 分类管理 | DELETE | `/api/categories/{id}` | 删除分类（无引用时） |
| 8 | 月度报表 | GET | `/api/reports/monthly` | 获取月度报表 |

**不变式**
- 所有接口前缀 `/api`；请求与响应均为 `application/json; charset=utf-8`。
- 所有响应使用统一结构 `{ code, message, data }`（spec §6.2）。
- 所有金额在接口层单位为**元**（最多 2 位小数）；数据库层为整数「分」，转换由后端完成（spec §7.7、R-17）。
- 所有"今天 / 当前月"由服务端按业务时区 `Asia/Shanghai` 计算（spec §8、R-06）。

---

## 2. 通用约定

### 2.1 统一响应结构（spec §6.2）

**成功**
```json
{ "code": 0, "message": "success", "data": {} }
```

**失败**
```json
{ "code": 1002, "message": "金额不合法", "data": null }
```

- `code`：`0` = 成功，非 0 = 业务错误；HTTP 状态码与错误码表一致。
- `data`：成功时为对象或数组；失败时固定为 `null`。

### 2.2 错误码与标准文案（严格对齐 spec §6.2、§9 E-01 ~ E-17）

> 同一 `code` 在不同场景可有不同 `message`（spec §6.2 注明：文案以 §9 为准）。下表为**逐场景**映射，实现时不得统一替换为笼统文案。

| code | HTTP | 触发场景（spec §9） | 标准 `message` |
| --- | --- | --- | --- |
| 0 | 200 | 成功 | `success` |
| 1001 | 400 | E-03 必填缺失 / 字段类型或格式非法 / Pydantic 校验失败 | `参数不合法` |
| 1001 | 400 | E-08 备注超长（> 100 个 Unicode 码点） | `备注长度超限` |
| 1001 | 400 | E-10 分类名称为空或超长（> 20 个 Unicode 码点） | `分类名称不合法` |
| 1002 | 400 | E-01 金额非法（空 / 非数字 / ≤ 0 / 超过 2 位小数） | `金额不合法` |
| 1003 | 400 | E-02 金额超出允许范围（> 99,999,999.99 元） | `金额超出允许范围` |
| 1004 | 400 | E-06 日期非法 | `日期不合法` |
| 1005 | 400 | E-07 月份非法 | `月份不合法` |
| 1006 | 400 | E-04 分类类型与收支类型不一致 | `分类类型与收支类型不一致` |
| 1007 | 404 | E-05 新增/编辑账单引用不存在的分类；E-17 删除不存在的分类 | `分类不存在` |
| 1008 | 404 | E-12 编辑 / 删除不存在的记录 | `记录不存在` |
| 1009 | 409 | E-09 分类重名（同类型下） | `该分类已存在` |
| 1010 | 409 | E-11 分类存在关联账单 | `该分类下存在记录，无法删除` |
| 1999 | 500 | E-14 数据库/服务端未捕获异常 | `服务器内部错误` |

- E-13（无数据）→ `0 / 200`；E-15 / E-16 为前端职责，无后端响应。
- FastAPI / Pydantic 字段校验失败默认 422，须由全局 `RequestValidationError` 处理器转换为 `1001 / 400`（architecture §9）。

### 2.3 通用数据类型（R-01、R-17）

> **金额单位（R-17）**：接口层（请求与响应）金额一律为「**元**」（最多 2 位小数）；数据库层为整数「**分**」。转换由后端唯一入口 `core/money.py` 完成，接口不暴露「分」。
> **金额类型（R-01）**：按语义拆分为三类，避免"单笔上限/正数约束"误加到汇总值上。

| 类型名 | JSON 类型 | 适用字段 | 取值域 |
| --- | --- | --- | --- |
| `Money` | number | 单笔账单 `amount`（**请求与响应**） | 元；`> 0`；`≤ 99,999,999.99`；最多 2 位小数 |
| `AggregateAmount` | number | `total_income`、`total_expense`、`expense_by_category[].amount` | 元；`≥ 0`（**允许 `0.00`**）；**不套用单笔金额上限**；保留 2 位小数 |
| `SignedAmount` | number | `balance` | 元；**可为负、可为零**；保留 2 位小数 |
| `Percentage` | number | `percentage` | `0.00`–`100.00`；保留 2 位小数 |
| `Id` | integer | 各类 ID | 正整数 |
| `TransactionType` | string enum | `type` | `income` \| `expense` |
| `Date` | string | `date` | 严格 `YYYY-MM-DD`（补零） |
| `Month` | string | `month` | 严格 `YYYY-MM`，月份 `01`–`12` |

> 三类金额在 JSON 中均为 `number`，差异体现在**取值域约束**上；请勿将 `Money` 的 `>0` 与上限约束套用到 `AggregateAmount` / `SignedAmount`。

### 2.4 通用参数校验规则（spec §5、§7，architecture §10）

| 字段 | 规则 | 违规错误码 |
| --- | --- | --- |
| `amount` | 数字；`> 0`；`≤ 99,999,999.99`；最多 2 位小数 | 1002 / 1003 |
| `type` | 仅 `income` / `expense` | 1001 |
| `category_id` | 必须存在，且分类 `type` 与请求 `type` 一致（**仅写入类接口校验**） | 1007 / 1006 |
| `date` | 严格 `YYYY-MM-DD`；`≥ 2000-01-01`；`≤` 业务时区今天 | 1004 |
| `note` | 可选；**≤ 100 个 Unicode 码点**（按码点计数，不区分是否 emoji） | 1001 / `备注长度超限` |
| `name` | 去首尾空格后 **1–20 个 Unicode 码点**；同类型下唯一 | 1001 / `分类名称不合法`；1009 |
| `month` | 严格 `YYYY-MM`（正则 `^\d{4}-(0[1-9]\|1[0-2])$`） | 1005 |

> **字符长度口径（R-06）**：统一表述为"按 Unicode 码点计数"。Python `len()` 与 SQLite `length()` 均按码点计数，二者一致；不再使用"emoji 计 1"的说法（组合 emoji 含多个码点）。

**统一校验原则（spec R-14 / AC-24）**：`POST /api/transactions` 与 `PUT /api/transactions/{id}` 使用**完全一致**的校验规则与校验函数，同一非法输入返回相同错误码与文案。

### 2.5 排序与精度

| 项 | 规则 | 依据 |
| --- | --- | --- |
| 账单列表排序 | `date DESC, id DESC` | spec R-12 |
| 分类列表排序 | 先按 `type`，再按 `id` 升序 | database-design 附录 G-03 |
| 报表分类排序 | 按 `amount` 降序 | spec §6.3 |
| 金额精度 | 接口层元（2 位小数）；后端全程整数分计算后再转元 | spec §7.7 |
| 金额单位 | 接口「元」/ 数据库「分」，接口层不暴露分 | spec R-17 |
| `percentage` | 后端唯一计算，保留 2 位小数；允许 ±0.01% 误差，各分类之和落在 `99.99%`–`100.01%` | spec R-10、R-21 |

### 2.6 通用错误响应 HTTP 状态码

| 情形 | `data` 形态 | `code` |
| --- | --- | --- |
| 成功（含 DELETE） | 对象 / 数组 / `null` | 0 |
| 参数或业务校验失败 | `null` | 1001–1006 |
| 资源不存在 | `null` | 1007 / 1008 |
| 冲突 | `null` | 1009 / 1010 |
| 服务端异常 | `null` | 1999 |

### 2.7 缺省值与测试可复现（R-08）

| 项 | 约定 |
| --- | --- |
| `month` 缺省行为 | 回退为业务时区（`Asia/Shanghai`）的**当前月**（与 spec §5.3、§6.1 一致） |
| 测试环境 | 后端进程时区固定为 `Asia/Shanghai`；"今天 / 当前月"由服务端统一计算，前端不参与 |
| 可复现要求 | **所有自动化测试与验收用例必须显式传入 `month`**（如 `?month=2026-10`），不得依赖缺省值，避免随运行日期漂移 |
| 说明 | 缺省值仅用于前端人工操作体验；它不是"返回全部月份"的语义 |

---

## 3. 接口详情

---

### 3.1 GET /api/transactions — 查询账单列表

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `GET` |
| **URL** | `/api/transactions` |
| **功能** | 按月份查看账单列表，支持按类型、分类进一步筛选；对应 spec US-04、§6.1 |

**Query 参数**

| 参数 | 类型 | 必填 | 默认 | 校验 |
| --- | --- | --- | --- | --- |
| `month` | `Month` | 否 | 业务时区当前月 | 严格 `YYYY-MM`，月份 01–12（违规 1005） |
| `type` | `TransactionType` | 否 | 无（不筛选） | 仅 `income` / `expense`（违规 1001 / `参数不合法`） |
| `category_id` | `Id` | 否 | 无（不筛选） | 正整数；**不校验分类是否存在**（无匹配返回 `[]`） |

**互斥/矛盾筛选行为（R-03、spec §6.1）**

| 情形 | 行为 |
| --- | --- |
| `type` 与 `category_id` 同时传入且**互相矛盾**（所选分类的 `type` 与所传 `type` 不一致） | 返回 `0 / HTTP 200`，`data: []`（**不返回 1006/1007**） |
| `category_id` 指向不存在的分类 | 返回 `0 / HTTP 200`，`data: []` |
| 筛选条件无任何匹配 | 返回 `0 / HTTP 200`，`data: []` |

**Path 参数**：无
**Request Body**：无

**成功响应 `data`**：**账单对象数组**（R-12，spec §6.1 明确）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 账单 ID |
| `amount` | `Money` | 金额（元，2 位小数） |
| `type` | `TransactionType` | 收支类型 |
| `category_id` | integer | 分类 ID |
| `date` | `Date` | 业务日期 |
| `note` | string \| null | 备注 |

> 列表项**不含** `category_name`（严格对齐 spec §6.2 示例）；前端用 `GET /api/categories` 的 `id → name` 映射渲染。

**错误响应**：`1005`（`月份不合法`）、`1001`（`参数不合法`）、`1999`（`服务器内部错误`）

**HTTP 状态码**：`200` / `400` / `500`

**JSON 示例**

请求：
```
GET /api/transactions?month=2026-10&type=expense&category_id=6
```
成功响应（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "id": 3, "amount": 33.33, "type": "expense", "category_id": 6, "date": "2026-10-05", "note": "午餐" },
    { "id": 6, "amount": 2100.00, "type": "expense", "category_id": 8, "date": "2026-10-04", "note": "买衣服" }
  ]
}
```
无数据 / 矛盾筛选的成功响应（HTTP 200）：
```json
{ "code": 0, "message": "success", "data": [] }
```
错误响应（HTTP 400）：
```json
{ "code": 1005, "message": "月份不合法", "data": null }
```

---

### 3.2 POST /api/transactions — 新增账单

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `POST` |
| **URL** | `/api/transactions` |
| **功能** | 新增一笔收入或支出账单；对应 spec US-01、§7.1 |

**Query 参数**：无
**Path 参数**：无

**Request Body**

| 字段 | 类型 | 必填 | 校验 |
| --- | --- | --- | --- |
| `amount` | `Money` | 是 | 数字；`> 0`；`≤ 99999999.99`；最多 2 位小数 |
| `type` | `TransactionType` | 是 | 仅 `income` / `expense` |
| `category_id` | `Id` | 是 | 分类必须存在（1007）且 `category.type == type`（1006） |
| `date` | `Date` | 是 | 严格 `YYYY-MM-DD`；`≥ 2000-01-01`；`≤` 业务时区今天 |
| `note` | string \| null | 否 | ≤ 100 个 Unicode 码点 |

**成功响应 `data`**：新建账单对象（字段同 §3.1，`amount` 为 `Money`）

**错误响应**

| code | HTTP | message |
| --- | --- | --- |
| 1001 | 400 | `参数不合法` / `备注长度超限` |
| 1002 | 400 | `金额不合法` |
| 1003 | 400 | `金额超出允许范围` |
| 1004 | 400 | `日期不合法` |
| 1006 | 400 | `分类类型与收支类型不一致` |
| 1007 | 404 | `分类不存在` |
| 1999 | 500 | `服务器内部错误` |

**HTTP 状态码**：`200` / `400` / `404` / `500`

**JSON 示例**

请求：
```json
{
  "amount": 33.33,
  "type": "expense",
  "category_id": 6,
  "date": "2026-10-05",
  "note": "午餐"
}
```
成功响应（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 14,
    "amount": 33.33,
    "type": "expense",
    "category_id": 6,
    "date": "2026-10-05",
    "note": "午餐"
  }
}
```
错误响应（HTTP 400，金额为 0）：
```json
{ "code": 1002, "message": "金额不合法", "data": null }
```
错误响应（HTTP 400，备注超长，E-08 专用文案）：
```json
{ "code": 1001, "message": "备注长度超限", "data": null }
```
错误响应（HTTP 404，分类不存在）：
```json
{ "code": 1007, "message": "分类不存在", "data": null }
```
错误响应（HTTP 400，类型与分类不一致）：
```json
{ "code": 1006, "message": "分类类型与收支类型不一致", "data": null }
```

---

### 3.3 PUT /api/transactions/{id} — 编辑账单

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `PUT` |
| **URL** | `/api/transactions/{id}` |
| **功能** | **全量覆盖**更新账单；复用与 POST 完全一致的校验；对应 spec US-02、§7.2 |

**Query 参数**：无

**Path 参数**

| 参数 | 类型 | 必填 | 校验 |
| --- | --- | --- | --- |
| `id` | `Id` | 是 | 正整数；非整数 → 1001 / `参数不合法`；对应账单不存在 → 1008 / `记录不存在` |

**Request Body**：与 §3.2 `POST /api/transactions` **完全一致**（字段、类型、必填、校验规则相同）

**成功响应 `data`**：更新后的账单对象（字段同 §3.1）

**错误响应**：`1001`（`参数不合法` / `备注长度超限`）、`1002`、`1003`、`1004`、`1006`、`1007`（`分类不存在`）、`1008`（`记录不存在`）、`1999`

**HTTP 状态码**：`200` / `400` / `404` / `500`

**JSON 示例**

请求：
```
PUT /api/transactions/14
```
```json
{
  "amount": 45.00,
  "type": "expense",
  "category_id": 6,
  "date": "2026-10-05",
  "note": "午餐（改）"
}
```
成功响应（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 14,
    "amount": 45.00,
    "type": "expense",
    "category_id": 6,
    "date": "2026-10-05",
    "note": "午餐（改）"
  }
}
```
错误响应（HTTP 404，账单不存在）：
```json
{ "code": 1008, "message": "记录不存在", "data": null }
```

---

### 3.4 DELETE /api/transactions/{id} — 删除账单

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `DELETE` |
| **URL** | `/api/transactions/{id}` |
| **功能** | 删除单条账单（前端需二次确认）；对应 spec US-03、§7.3 |

**Query 参数**：无

**Path 参数**

| 参数 | 类型 | 必填 | 校验 |
| --- | --- | --- | --- |
| `id` | `Id` | 是 | 正整数；非整数 → 1001；账单不存在 → 1008 / `记录不存在` |

**Request Body**：无

**成功响应 `data`**：`null`

**错误响应**：`1008`（`记录不存在`）、`1999`（`服务器内部错误`）

**HTTP 状态码**：`200` / `404` / `500`

**JSON 示例**

请求：
```
DELETE /api/transactions/14
```
成功响应（HTTP 200）：
```json
{ "code": 0, "message": "success", "data": null }
```
错误响应（HTTP 404）：
```json
{ "code": 1008, "message": "记录不存在", "data": null }
```

---

### 3.5 GET /api/categories — 查询分类列表

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `GET` |
| **URL** | `/api/categories` |
| **功能** | 查询分类列表，可按收支类型筛选；分类管理页按收入/支出分组展示；对应 spec US-05、US-08 |

**Query 参数**

| 参数 | 类型 | 必填 | 默认 | 校验 |
| --- | --- | --- | --- | --- |
| `type` | `TransactionType` | 否 | 无（返回全部） | 仅 `income` / `expense`（违规 1001 / `参数不合法`） |

**Path 参数**：无
**Request Body**：无

**成功响应 `data`**：分类对象数组（排序：先 `type`，再 `id` 升序）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 分类 ID |
| `name` | string | 分类名称（1–20 个 Unicode 码点） |
| `type` | `TransactionType` | 分类归属的收支类型 |

> `created_at` 为内部审计字段，不对外暴露。

**错误响应**：`1001`（`参数不合法`）、`1999`

**HTTP 状态码**：`200` / `400` / `500`

**JSON 示例**

请求：
```
GET /api/categories?type=expense
```
成功响应（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "id": 6,  "name": "餐饮",   "type": "expense" },
    { "id": 7,  "name": "交通",   "type": "expense" },
    { "id": 13, "name": "其他支出", "type": "expense" }
  ]
}
```
错误响应（HTTP 400）：
```json
{ "code": 1001, "message": "参数不合法", "data": null }
```

---

### 3.6 POST /api/categories — 新增分类

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `POST` |
| **URL** | `/api/categories` |
| **功能** | 新增收入或支出分类；对应 spec US-06、US-08、§5.2 |

**Query 参数**：无
**Path 参数**：无

**Request Body**

| 字段 | 类型 | 必填 | 校验 |
| --- | --- | --- | --- |
| `name` | string | 是 | 去首尾空格后 1–20 个 Unicode 码点；同 `type` 下不可重名（1009） |
| `type` | `TransactionType` | 是 | 仅 `income` / `expense` |

**成功响应 `data`**：新建分类对象（`id`、`name`、`type`）

**错误响应**

| code | HTTP | message |
| --- | --- | --- |
| 1001 | 400 | `分类名称不合法`（E-10） |
| 1009 | 409 | `该分类已存在` |
| 1999 | 500 | `服务器内部错误` |

**HTTP 状态码**：`200` / `400` / `409` / `500`

**JSON 示例**

请求：
```json
{ "name": "宠物", "type": "expense" }
```
成功响应（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": { "id": 14, "name": "宠物", "type": "expense" }
}
```
错误响应（HTTP 400，名称非法，E-10 专用文案）：
```json
{ "code": 1001, "message": "分类名称不合法", "data": null }
```
错误响应（HTTP 409，重名）：
```json
{ "code": 1009, "message": "该分类已存在", "data": null }
```

---

### 3.7 DELETE /api/categories/{id} — 删除分类

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `DELETE` |
| **URL** | `/api/categories/{id}` |
| **功能** | 删除无账单引用的分类；有引用时拒绝；对应 spec US-07、§7.5、R-04 |

**Query 参数**：无

**Path 参数**

| 参数 | 类型 | 必填 | 校验 |
| --- | --- | --- | --- |
| `id` | `Id` | 是 | 正整数；非整数 → 1001；分类不存在 → 1007 / `分类不存在`（E-17） |

**Request Body**：无

**成功响应 `data`**：`null`

**行为说明**

| 情形 | 行为 | code / HTTP |
| --- | --- | --- |
| 分类无任何账单引用 | 删除成功，`data: null` | 0 / 200 |
| 分类被账单引用 | 拒绝，`message: 该分类下存在记录，无法删除` | 1010 / 409 |
| 分类不存在（含已删除） | `message: 分类不存在` | 1007 / 404 |

> **R-04**：本契约**不返回引用条数**，也不出现"存在 N 条记录"之类无 spec 依据的提示；文案严格为 spec §9 E-11 的 `该分类下存在记录，无法删除`。
> **无孤儿账单**：应用层引用计数 + 数据库 `ON DELETE RESTRICT` 双重保障（spec §7.5 R-18）。

**错误响应**：`1007`（`分类不存在`）、`1010`（`该分类下存在记录，无法删除`）、`1999`

**HTTP 状态码**：`200` / `404` / `409` / `500`

**JSON 示例**

请求：
```
DELETE /api/categories/6
```
成功响应（HTTP 200，无引用时）：
```json
{ "code": 0, "message": "success", "data": null }
```
错误响应（HTTP 409，被引用）：
```json
{ "code": 1010, "message": "该分类下存在记录，无法删除", "data": null }
```
错误响应（HTTP 404，分类不存在 — E-17）：
```json
{ "code": 1007, "message": "分类不存在", "data": null }
```

---

### 3.8 GET /api/reports/monthly — 月度报表

| 项 | 内容 |
| --- | --- |
| **HTTP 方法** | `GET` |
| **URL** | `/api/reports/monthly` |
| **功能** | 返回指定月份的收入总额、支出总额、结余与支出分类占比；对应 spec US-09、US-10、§6.3、§7.6 |

**Query 参数**

| 参数 | 类型 | 必填 | 默认 | 校验 |
| --- | --- | --- | --- | --- |
| `month` | `Month` | 否 | 业务时区当前月 | 严格 `YYYY-MM`，月份 01–12（违规 1005 / `月份不合法`） |

> 测试可复现要求见 §2.7：验收用例必须显式传 `month`。

**Path 参数**：无
**Request Body**：无

**成功响应 `data`**

| 字段 | 类型（R-01） | 说明 |
| --- | --- | --- |
| `month` | `Month` | 报表所属月份 |
| `total_income` | `AggregateAmount` | 当月收入总额（元，2 位小数；允许 `0.00`，无单笔上限） |
| `total_expense` | `AggregateAmount` | 当月支出总额（元，2 位小数；允许 `0.00`，无单笔上限） |
| `balance` | `SignedAmount` | 当月结余 = `total_income − total_expense`，**可为负** |
| `expense_by_category` | array | 支出分类统计，按 `amount` 降序；无支出时为空数组 |

`expense_by_category[]` 元素：

| 字段 | 类型（R-01） | 说明 |
| --- | --- | --- |
| `category_id` | integer | 分类 ID |
| `category_name` | string | 分类名称 |
| `amount` | `AggregateAmount` | 该分类支出金额（元，2 位小数；≥ 0） |
| `percentage` | `Percentage` | 占比（%），**后端唯一计算**，保留 2 位小数 |

> **金额类型一致性（R-01）**：`total_income` / `total_expense` / `expense_by_category[].amount` 均为 `AggregateAmount`（≥ 0，不套用单笔上限）；`balance` 为 `SignedAmount`（可负）。**只有单笔账单 `amount` 使用 `Money`**。

**口径（spec §7.6 / §6.3）**
- 月份归属按业务日期 `date`；区间 `[当月第一天（含）, 下月第一天（不含）)`，按自然月进位，跨年正确（`2026-12 → 2027-01-01`）。
- 所有汇总在整数「分」上计算，输出时统一转「元」并保留 2 位小数。
- `percentage = 该分类支出 ÷ 总支出 × 100`，保留 2 位小数；允许 ±0.01% 误差。
- 空数据处理（spec §6.3、§7.8、E-13）：
  - `total_income` / `total_expense` 无数据时均为 `0.00`；
  - 总支出为 0 时 `expense_by_category` 为 `[]`。

**前端空状态判定（依赖 §3.8 返回值）**
| 条件 | 前端展示（spec §7.8） |
| --- | --- |
| `total_income == 0 且 total_expense == 0` | 卡片均 `¥0.00`；饼图区"本月暂无数据" |
| `total_income > 0 且 total_expense == 0` | 饼图区"本月暂无支出数据" |
| `total_expense > 0` | 正常饼图，直接使用后端 `percentage` |

**错误响应**：`1005`（`月份不合法`）、`1999`（`服务器内部错误`）

**HTTP 状态码**：`200` / `400` / `500`

**JSON 示例**

**① 常规月份** `GET /api/reports/monthly?month=2026-10`（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "month": "2026-10",
    "total_income": 12500.00,
    "total_expense": 5145.83,
    "balance": 7354.17,
    "expense_by_category": [
      { "category_id": 9, "category_name": "居住", "amount": 3000.00, "percentage": 58.30 },
      { "category_id": 8, "category_name": "购物", "amount": 2100.00, "percentage": 40.81 },
      { "category_id": 6, "category_name": "餐饮", "amount": 33.33,   "percentage": 0.65  },
      { "category_id": 7, "category_name": "交通", "amount": 12.50,   "percentage": 0.24  }
    ]
  }
}
```

**② 跨年月份（R-07）** `GET /api/reports/monthly?month=2025-12`（HTTP 200）：
> 区间为 `[2025-12-01, 2026-01-01)`。测试数据中 `2025-12-31` 的 50.00 元计入本月，`2026-01-01` 的 60.00 元**不计入**（属 2026-01）。同时验证 `balance` 可为负。
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "month": "2025-12",
    "total_income": 0.00,
    "total_expense": 50.00,
    "balance": -50.00,
    "expense_by_category": [
      { "category_id": 6, "category_name": "餐饮", "amount": 50.00, "percentage": 100.00 }
    ]
  }
}
```
> 相邻月份 `GET /api/reports/monthly?month=2026-01` 返回 `total_expense: 60.00`，用于证明跨年边界两侧数据互不混入。

**③ 空月份** `GET /api/reports/monthly?month=2026-02`（HTTP 200）：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "month": "2026-02",
    "total_income": 0.00,
    "total_expense": 0.00,
    "balance": 0.00,
    "expense_by_category": []
  }
}
```

**④ 错误**（HTTP 400）：
```json
{ "code": 1005, "message": "月份不合法", "data": null }
```

---

## 4. 数据模型汇总（Request / Response Schema）

| Schema | 使用接口 | 字段 |
| --- | --- | --- |
| `ApiResponse<T>` | 全部 | `code: int`、`message: string`、`data: T \| null` |
| `TransactionCreate` | POST /transactions | `amount: Money`*、`type: TransactionType`*、`category_id: Id`*、`date: Date`*、`note: string\|null` |
| `TransactionUpdate` | PUT /transactions/{id} | 字段与 `TransactionCreate` **完全一致** |
| `TransactionOut` | GET / POST / PUT `/transactions` | `id`、`amount: Money`、`type`、`category_id`、`date`、`note` |
| `TransactionQuery` | GET /transactions | `month?`、`type?`、`category_id?`（矛盾时返回 `[]`） |
| `CategoryCreate` | POST /categories | `name: string`*、`type: TransactionType`* |
| `CategoryOut` | GET / POST `/categories` | `id`、`name`、`type` |
| `CategoryQuery` | GET /categories | `type?` |
| `MonthlyReportOut` | GET /reports/monthly | `month: Month`、`total_income: AggregateAmount`、`total_expense: AggregateAmount`、`balance: SignedAmount`、`expense_by_category: CategoryExpenseItem[]` |
| `CategoryExpenseItem` | 报表内嵌 | `category_id`、`category_name`、`amount: AggregateAmount`、`percentage: Percentage` |

（`*` = 必填）
（金额类型定义见 §2.3：`Money` 仅用于单笔账单；`AggregateAmount` / `SignedAmount` 仅用于报表汇总）

---

## 5. 接口与数据库的对应关系

| 接口 | 主要数据操作 | 依赖数据库设计 |
| --- | --- | --- |
| GET /transactions | `SELECT ... WHERE date >= :start AND date < :end [AND type=?] [AND category_id=?] ORDER BY date DESC, id DESC` | `ix_transactions_date`、`ix_transactions_type`、`ix_transactions_category_id` |
| POST /transactions | `INSERT INTO transactions`（元 → 分） | `amount` CHECK、FK、`type` CHECK、`date` CHECK |
| PUT /transactions/{id} | `UPDATE transactions SET ... , updated_at=?` | 同上 + 应用层维护 `updated_at` |
| DELETE /transactions/{id} | `DELETE FROM transactions WHERE id=?` | 主键 |
| GET /categories | `SELECT ... [WHERE type=?] ORDER BY type, id` | `ux_categories_name_type` |
| POST /categories | `INSERT INTO categories`（去空格后写入） | `ux_categories_name_type` 唯一索引 |
| DELETE /categories/{id} | 存在性检查 + 引用计数 `COUNT(*)` + `DELETE` | 主键 + FK `ON DELETE RESTRICT` |
| GET /reports/monthly | 收入 SUM、支出 SUM、`GROUP BY category_id`（JOIN categories） | `ix_transactions_date`、`ix_transactions_category_id` |

---

# 附录：一致性检查

## 一、API 是否覆盖 Spec 中所有必做功能

| spec 功能 | 覆盖接口 | 状态 |
| --- | --- | --- |
| 收支记录：新增（US-01） | `POST /api/transactions` | ✅ |
| 收支记录：编辑（US-02） | `PUT /api/transactions/{id}` | ✅ |
| 收支记录：删除（US-03） | `DELETE /api/transactions/{id}` | ✅ |
| 收支记录：查看/按月份筛选（US-04） | `GET /api/transactions` | ✅ |
| 分类管理：查看（US-05、US-08） | `GET /api/categories` | ✅ |
| 分类管理：新增（US-06、US-08） | `POST /api/categories` | ✅ |
| 分类管理：删除（US-07） | `DELETE /api/categories/{id}` | ✅ |
| 月度报表：收入/支出/结余（US-09） | `GET /api/reports/monthly` | ✅ |
| 月度报表：分类金额与占比饼图（US-10） | `GET /api/reports/monthly`（`expense_by_category`） | ✅ |

**结论：spec §3 的 9 项 P0 功能、US-01 ~ US-10 全覆盖，端点恰好 8 个，无多余接口。**

## 二、API 是否能够由数据库实现

**全部可实现，无阻塞项。**

| 接口能力 | 数据库支撑 | 状态 |
| --- | --- | --- |
| 账单按月筛选、排序 | `transactions.date` TEXT（字典序=时间序）+ `ix_transactions_date` | ✅ |
| 账单增/改/删 | `transactions` 表 + CHECK 约束 | ✅ |
| 互斥筛选返回 `[]` | `WHERE type=? AND category_id=?` 自然无匹配 | ✅ |
| 分类筛选、分组展示 | `categories` + `ux_categories_name_type` | ✅ |
| 分类重名检测 | 唯一索引 `(name,type)` | ✅ |
| 删除被引用分类被拒 | `ON DELETE RESTRICT` + 应用层引用计数 | ✅ |
| 删除不存在分类 → 1007 | 存在性查询 | ✅ |
| 收入/支出总额、结余 | `SUM(amount)`（整数分）+ 应用层减法 | ✅ |
| 分类支出统计与占比 | `GROUP BY category_id` + JOIN + 后端百分比计算 | ✅ |
| 跨年月份区间 | `date >= '2025-12-01' AND date < '2026-01-01'` | ✅ |

> 两项规则由**应用层**实现（非数据库）：`type` 与分类 `type` 一致（A-01）、日期 ≤ 业务时区今天（A-03）——与 spec §4.2 R-02 及 database-design §4.2 一致。

## 三、字段名称是否完全一致

| 字段 | spec.md | database-design.md | 本文档 | 一致性 |
| --- | --- | --- | --- | --- |
| 金额 | `amount`（元/接口） | `amount`（分/库） | `amount`（元，`Money`） | ✅ 同名，单位按层区分（R-17 已标注） |
| 收支类型 | `type` | `type` | `type` | ✅ |
| 分类外键 | `category_id` | `category_id` | `category_id` | ✅ |
| 日期 | `date` | `date` | `date` | ✅ |
| 备注 | `note` | `note` | `note` | ✅ |
| 分类名称 | `name` | `name` | `name` | ✅ |
| 收入总额 | `total_income` | — | `total_income`（`AggregateAmount`） | ✅ |
| 支出总额 | `total_expense` | — | `total_expense`（`AggregateAmount`） | ✅ |
| 结余 | `balance` | — | `balance`（`SignedAmount`） | ✅ |
| 分类统计数组 | `expense_by_category` | — | 同左 | ✅ |
| 分类统计项 | `category_id` / `category_name` / `amount` / `percentage` | — | 同左 | ✅ |
| 月份 | `month` | — | `month` | ✅ |
| 统一响应 | `code` / `message` / `data` | — | 同左 | ✅ |

**结论：字段名称与 spec 完全一致，未自行发明命名。**

## 四、错误码是否一致

| 错误码 | spec §6.2 / §9 | 本文档 | 一致性 |
| --- | --- | --- | --- |
| 0 | ✅ | ✅ | ✅ |
| 1001（含 E-08/E-10 细分文案） | ✅ | ✅ 逐场景对齐 | ✅ |
| 1002–1010 | ✅ | ✅ 全部沿用 | ✅ |
| 1999 | ✅ | ✅ | ✅ |
| E-17 删除不存在分类 → 1007 | ✅（spec v1.2 新增） | ✅ | ✅ |

**结论：错误码与文案 100% 取自 spec §6.2 / §9，未新增、未改动语义与 HTTP 状态码映射。**

## 五、请求和响应数据类型是否一致

| 数据类型 | 约定 | 一致性 |
| --- | --- | --- |
| 单笔 `amount` 输入 | `Money`（元，>0，≤99999999.99，≤2 位小数） | 与 spec §5.1 一致 ✅ |
| 单笔 `amount` 输出 | `Money`（元，2 位小数） | 与 spec §6.2 示例一致 ✅ |
| `total_income` / `total_expense` | `AggregateAmount`（元，≥0，无单笔上限，2 位小数） | 与 spec §6.3 一致 ✅（R-01 已修复） |
| `balance` | `SignedAmount`（可为负，2 位小数） | 与 spec R-22 一致 ✅（R-01 已修复） |
| `expense_by_category[].amount` | `AggregateAmount`（≥0） | ✅ |
| `percentage` | number（2 位小数） | 与 spec §6.3 一致 ✅ |
| `type` | enum `income`/`expense` | 与 spec §4.1/§4.2 一致 ✅ |
| `date` / `month` | string `YYYY-MM-DD` / `YYYY-MM` | 与 spec §4.2/§5.3 一致 ✅ |
| `code` | integer | ✅ |

**结论：请求与响应数据类型全部一致，报表内金额类型定义已统一（R-01 解决）。**

## 六、是否发现设计冲突

**无实质冲突。** 原 v1.0 遗留的差异均已裁决并落地：

| 编号 | 原差异 | 处置 | 状态 |
| --- | --- | --- | --- |
| C-01 | 任务描述用 `income_total` / `expense_total`，spec 用 `total_income` / `total_expense` | 以 spec 为准，采用 `total_income` / `total_expense` | ✅ 保持 |
| C-02 | POST 惯例 201 vs spec 的 200 | 遵循 spec，统一 `200` | ✅ 保持 |
| C-03 | spec §7.5 曾提"存在 N 条记录"，与 §9 文案不一致 | **spec v1.2 已删除"N 条"表述**，契约统一为 `该分类下存在记录，无法删除`（R-04） | ✅ 已解决 |
| C-04 | 列表项是否含 `category_name` | 严格按 spec §6.2，不含；前端用 `/api/categories` 映射 | ✅ 保持 |
| C-05 | 分类对象是否含 `created_at` | 不暴露 | ✅ 保持 |
| C-06 | 列表 `month` 缺省语义 | 缺省 = 业务时区当前月；测试须显式传 `month`（§2.7） | ✅ 已明确 |
| C-07 | DELETE 成功的 `data` 形态 | 统一 `data: null` | ✅ 保持 |
| 新增 | 互斥筛选参数行为 | 矛盾/无匹配 → `[]`（200），spec §6.1 与本文档 §3.1 一致 | ✅ 已明确 |

## 七、R-01 ~ R-17 修复对照

| 编号 | 问题 | 修复位置 | 状态 |
| --- | --- | --- | --- |
| R-01 | `Money` 被误用于汇总 | §2.3 拆分 `Money` / `AggregateAmount` / `SignedAmount`；§3.8、§4 同步 | ✅ |
| R-02 | 1001 文案笼统 | §2.2 逐场景文案表；§3.2 / §3.6 给出 E-08 / E-10 专用文案 | ✅ |
| R-03 | 互斥筛选未定义 | §3.1 行为表；spec §6.1 同步；AC-27 | ✅ |
| R-04 | "存在 N 条"无依据 | spec §7.5 删除该表述；§3.7 明确不返回条数 | ✅ |
| R-06 | emoji 长度口径矛盾 | §2.4 统一为"按 Unicode 码点计数"；spec §5.1 同步 | ✅ |
| R-07 | 缺跨年示例 | §3.8 示例 ②（`2025-12`，含 2026-01 对照说明） | ✅ |
| R-08 | 缺省值致测试不可复现 | §2.7 缺省与测试约定；spec §5.3 同步 | ✅ |
| R-17 | 单位混淆 | §2.3 / §2.5 显式标注；spec §6.2 同步 | ✅ |
"""账单数据契约（spec §5.1 / §6.1、api-design §3.1–§3.4、§4）。

设计要点：
- `amount` / `date` 声明为 Any，让**非数字金额 → 1002**、**非法日期 → 1004**
  由 core.validators 统一产生（spec E-01 / E-06 指定的错误码）；
  若在此处用严格类型，会先被 Pydantic 拦成 1001，与 spec 不符。
- `TransactionUpdate` 与 `TransactionCreate` 字段、校验完全一致
  （spec §5.1 R-14 / AC-24），实现上共用同一个基类。
- 其余字段（`type` / `category_id`）由 Pydantic 做结构校验，违规 → 1001（spec E-03）。
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

TransactionType = Literal["income", "expense"]


class TransactionCreate(BaseModel):
    """新增账单请求体（金额单位为「元」）。"""

    amount: Any
    type: TransactionType
    category_id: int
    date: Any
    note: str | None = None


class TransactionUpdate(TransactionCreate):
    """编辑账单请求体：与新增完全一致（PUT 全量覆盖）。"""


class TransactionOut(BaseModel):
    """账单响应体（金额单位为「元」，保留 2 位小数）。"""

    id: int
    amount: float
    type: TransactionType
    category_id: int
    date: str
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionQuery(BaseModel):
    """账单列表查询参数（api-design §3.1 + 选做功能 2 搜索）。

    - 普通模式：`month` 缺省回退业务时区当前月；
    - 搜索模式：提供 `start_date` / `end_date` / `keyword` 任一参数时，
      按日期范围与备注关键词跨月查询，此时 `month` 不生效；
    - `type` 与 `category_id` 两种模式下都生效；矛盾或无匹配时返回 `[]`。
    """

    month: str | None = None
    type: TransactionType | None = None
    category_id: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    keyword: str | None = None
"""金额「元 / 分」转换的唯一入口（spec §7.7、database-design §3.1）。

接口层单位为「元」，数据库层单位为整数「分」。
禁止在 router / service / model 内散落 ×100 或 ÷100。
"""

from decimal import ROUND_HALF_UP, Decimal


def yuan_to_cents(amount_yuan: Decimal) -> int:
    """元 → 分（×100 取整）。入参应为已通过校验的金额。"""
    return int((amount_yuan * 100).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_yuan(amount_cents: int) -> float:
    """分 → 元（保留 2 位小数），用于接口输出。"""
    return float(Decimal(amount_cents) / Decimal(100))
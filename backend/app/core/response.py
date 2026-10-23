"""统一响应结构组装（spec §6.2、architecture §5 core/response.py）。

所有接口的成功响应统一为 {code: 0, message: "success", data: ...}。
错误响应的组装与全局异常处理器在后续 MVP 落地。
"""

from typing import Any


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    """组装成功响应体。"""
    return {"code": 0, "message": message, "data": data}
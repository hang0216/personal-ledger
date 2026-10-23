"""统一响应包装（spec §6.2、api-design §4 ApiResponse<T>）。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """所有接口的统一响应结构：{code, message, data}。"""

    code: int = 0
    message: str = "success"
    data: T | None = None
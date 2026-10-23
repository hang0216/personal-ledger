"""全局异常处理器（architecture §9）。

三层统一错误出口，出口唯一：
① RequestValidationError（Pydantic 结构校验）→ 1001 / HTTP 400
② AppError（业务校验）→ 对应 code / HTTP
③ 兜底 Exception → 1999 / HTTP 500（记录日志，不返回堆栈）

注：备注超长（E-08）文案为"备注长度超限"，由业务层显式构造 AppError 携带。
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 实例上注册统一异常处理器。"""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # spec E-03：FastAPI 默认 422 需转换为统一结构 1001 / HTTP 400
        return JSONResponse(
            status_code=400,
            content={
                "code": ErrorCode.PARAM_INVALID,
                "message": "参数不合法",
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # spec E-14：不泄露堆栈
        logger.exception("未捕获异常：%s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "服务器内部错误",
                "data": None,
            },
        )
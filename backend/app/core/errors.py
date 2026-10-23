"""错误码与业务异常（spec §6.2 / §9、api-design §2.2）。

错误码与标准文案严格取自 spec.md，不新增、不改语义：
    1001 参数校验失败 / 备注长度超限
    1002 金额不合法
    1003 金额超出允许范围
    1004 日期不合法
    1005 月份不合法
    1006 分类类型与收支类型不一致
    1007 分类不存在
    1008 记录不存在
    1009 该分类已存在
    1010 该分类下存在记录，无法删除
    1999 服务器内部错误
"""


class ErrorCode:
    """业务错误码常量（spec §6.2）。"""

    OK = 0
    PARAM_INVALID = 1001
    AMOUNT_INVALID = 1002
    AMOUNT_OUT_OF_RANGE = 1003
    DATE_INVALID = 1004
    MONTH_INVALID = 1005
    CATEGORY_TYPE_MISMATCH = 1006
    CATEGORY_NOT_FOUND = 1007
    TRANSACTION_NOT_FOUND = 1008
    CATEGORY_NAME_DUPLICATE = 1009
    CATEGORY_IN_USE = 1010
    INTERNAL_ERROR = 1999


# code -> HTTP 状态码（spec §6.2 错误码表）
_HTTP_STATUS_BY_CODE: dict[int, int] = {
    ErrorCode.PARAM_INVALID: 400,
    ErrorCode.AMOUNT_INVALID: 400,
    ErrorCode.AMOUNT_OUT_OF_RANGE: 400,
    ErrorCode.DATE_INVALID: 400,
    ErrorCode.MONTH_INVALID: 400,
    ErrorCode.CATEGORY_TYPE_MISMATCH: 400,
    ErrorCode.CATEGORY_NOT_FOUND: 404,
    ErrorCode.TRANSACTION_NOT_FOUND: 404,
    ErrorCode.CATEGORY_NAME_DUPLICATE: 409,
    ErrorCode.CATEGORY_IN_USE: 409,
    ErrorCode.INTERNAL_ERROR: 500,
}


class AppError(Exception):
    """业务异常的唯一载体；由 core.exceptions 统一转为 {code, message, data:null}。"""

    def __init__(self, code: int, message: str | None = None) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "请求失败")
        self.http_status = _HTTP_STATUS_BY_CODE.get(code, 400)
        super().__init__(self.message)


# code -> 默认标准文案（spec §9）
DEFAULT_MESSAGES: dict[int, str] = {
    ErrorCode.PARAM_INVALID: "参数不合法",
    ErrorCode.AMOUNT_INVALID: "金额不合法",
    ErrorCode.AMOUNT_OUT_OF_RANGE: "金额超出允许范围",
    ErrorCode.DATE_INVALID: "日期不合法",
    ErrorCode.MONTH_INVALID: "月份不合法",
    ErrorCode.CATEGORY_TYPE_MISMATCH: "分类类型与收支类型不一致",
    ErrorCode.CATEGORY_NOT_FOUND: "分类不存在",
    ErrorCode.TRANSACTION_NOT_FOUND: "记录不存在",
    ErrorCode.CATEGORY_NAME_DUPLICATE: "该分类已存在",
    ErrorCode.CATEGORY_IN_USE: "该分类下存在记录，无法删除",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
}
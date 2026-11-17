"""统一的应用异常类型。

界面层只需要捕获 :class:`AppError`，把 ``str(exc)`` 直接展示给用户，
因此所有面向用户的文案都必须是中文且含义明确。
"""

from __future__ import annotations


class AppError(Exception):
    """可以直接展示给用户的业务错误。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    """输入校验失败（必填、格式、时间区间等）。"""


class ConflictError(AppError):
    """时间冲突。"""

    def __init__(self, message: str, conflicts: list[object] | None = None) -> None:
        super().__init__(message)
        self.conflicts = conflicts or []


class DataFileError(AppError):
    """数据文件读取或写入失败。"""

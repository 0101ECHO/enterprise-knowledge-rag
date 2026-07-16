"""
自定义异常体系与全局异常处理
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str = "服务内部错误",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, resource: str = "资源", resource_id: str = ""):
        super().__init__(
            message=f"{resource}不存在: {resource_id}" if resource_id else f"{resource}不存在",
            status_code=404,
            error_code="NOT_FOUND",
        )


class PermissionDeniedException(AppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message, status_code=403, error_code="PERMISSION_DENIED"
        )


class ValidationException(AppException):
    def __init__(self, message: str = "参数校验失败", details: dict | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class DocumentProcessingException(AppException):
    def __init__(self, message: str = "文档处理失败", details: dict | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="DOC_PROCESSING_ERROR",
            details=details,
        )


class LLMException(AppException):
    def __init__(self, message: str = "LLM 服务异常"):
        super().__init__(
            message=message, status_code=502, error_code="LLM_ERROR"
        )


class VectorStoreException(AppException):
    def __init__(self, message: str = "向量数据库异常"):
        super().__init__(
            message=message, status_code=502, error_code="VECTOR_STORE_ERROR"
        )


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        from app.core.logging import log
        log.warning(
            f"AppException: {exc.error_code} - {exc.message} | "
            f"path={request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        from app.core.logging import log
        log.exception(
            f"Unhandled exception: {exc} | path={request.url.path}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": "服务内部错误，请稍后重试",
            },
        )

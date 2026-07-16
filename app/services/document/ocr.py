"""
OCR 服务 - 图片文字识别
基于 RapidOCR (onnxruntime)，支持中英文
"""

from typing import Optional
from app.core.config import settings
from app.core.logging import log


class OCRService:
    """OCR 服务单例"""

    _instance: Optional["OCRService"] = None
    _engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None and settings.OCR_ENABLED:
            self._init_engine()

    def _init_engine(self):
        """初始化 OCR 引擎"""
        try:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
            log.info("OCR 引擎初始化成功 (RapidOCR)")
        except ImportError:
            log.warning("RapidOCR 未安装，OCR 功能不可用")
        except Exception as e:
            log.error(f"OCR 引擎初始化失败: {e}")

    def extract_text(self, image_path: str) -> str:
        """对图片执行 OCR，返回识别文本

        Args:
            image_path: 图片文件路径

        Returns:
            识别出的文本
        """
        if not self._engine:
            log.warning("OCR 引擎未初始化，跳过")
            return ""

        try:
            result, _ = self._engine(image_path)
            if result:
                texts = [item[1] for item in result]
                text = "\n".join(texts)
                log.debug(f"OCR 识别完成: {image_path}, 字符数={len(text)}")
                return text
        except Exception as e:
            log.error(f"OCR 识别失败: {image_path}, 错误: {e}")

        return ""

    def extract_text_from_bytes(self, image_bytes: bytes) -> str:
        """对图片字节执行 OCR"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            return self.extract_text(tmp_path)
        finally:
            os.unlink(tmp_path)


# 全局单例
ocr_service = OCRService()

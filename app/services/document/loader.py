"""
文档加载器 - 支持多格式文档加载与统一解析
格式: PDF, Word(docx), HTML/网页, Markdown, TXT, 图片(OCR)
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from app.core.logging import log
from app.services.document.parser import (
    parse_pdf,
    parse_docx,
    parse_html,
    parse_markdown,
    parse_text,
    parse_image,
)
from app.services.document.chunker import TextChunker, ChunkResult


@dataclass
class ParsedDocument:
    """解析后的文档结构"""

    title: str = ""
    file_type: str = ""
    pages: list[dict] = field(default_factory=list)  # [{page: 1, text: "...", tables: [...], images: [...]}]
    metadata: dict = field(default_factory=dict)
    raw_text: str = ""

    def get_full_text(self) -> str:
        """获取完整文本"""
        if self.raw_text:
            return self.raw_text
        return "\n\n".join(p.get("text", "") for p in self.pages)


# 文件类型 -> 解析器映射
PARSER_MAP = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "doc": parse_docx,
    "html": parse_html,
    "htm": parse_html,
    "md": parse_markdown,
    "markdown": parse_markdown,
    "txt": parse_text,
    "text": parse_text,
    "png": parse_image,
    "jpg": parse_image,
    "jpeg": parse_image,
    "bmp": parse_image,
    "tiff": parse_image,
    "tif": parse_image,
    "webp": parse_image,
}


def get_file_type(file_path: str) -> str:
    """从文件路径推断文件类型"""
    ext = Path(file_path).suffix.lower().lstrip(".")
    return ext


class DocumentLoader:
    """统一文档加载器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunker = TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def load_and_parse(self, file_path: str, file_type: Optional[str] = None) -> ParsedDocument:
        """加载并解析文档

        Args:
            file_path: 文件路径
            file_type: 指定文件类型(可选)，不指定则从扩展名推断

        Returns:
            ParsedDocument: 解析后的文档
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ftype = file_type or get_file_type(file_path)
        log.info(f"开始加载文档: {file_path} (类型: {ftype})")

        parser = PARSER_MAP.get(ftype)
        if parser is None:
            raise ValueError(f"不支持的文件类型: {ftype}")

        parsed = parser(file_path)
        parsed.file_type = ftype
        parsed.metadata["file_path"] = file_path
        parsed.metadata["file_size"] = os.path.getsize(file_path)

        log.info(
            f"文档加载完成: {parsed.title or file_path}, "
            f"页数={len(parsed.pages)}, 文本长度={len(parsed.get_full_text())}"
        )
        return parsed

    def load_and_chunk(self, file_path: str, file_type: Optional[str] = None) -> ChunkResult:
        """加载文档并直接分块

        Returns:
            ChunkResult: 包含分块列表和文档元数据
        """
        parsed = self.load_and_parse(file_path, file_type)
        return self.chunker.chunk_document(parsed)

    def load_from_url(self, url: str) -> ParsedDocument:
        """从 URL 加载网页文档"""
        import httpx

        log.info(f"从 URL 加载文档: {url}")
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()

        # 保存到临时文件再解析
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".html", delete=False
        ) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            parsed = parse_html(tmp_path)
            parsed.metadata["source_url"] = url
            parsed.metadata["file_size"] = len(response.content)
            return parsed
        finally:
            os.unlink(tmp_path)

"""
文本分块器 - 智能分块，保留表格结构与上下文连续性
支持: 递归字符分块、表格整体保留、分块元数据
"""

from dataclasses import dataclass, field
from typing import Optional
import re

from app.core.config import settings
from app.core.logging import log
from app.services.document.loader import ParsedDocument


@dataclass
class Chunk:
    """单个分块"""

    content: str
    chunk_type: str = "text"  # text / table / image_caption
    chunk_index: int = 0
    page: int = 1
    metadata: dict = field(default_factory=dict)


@dataclass
class ChunkResult:
    """分块结果"""

    chunks: list[Chunk] = field(default_factory=list)
    document_title: str = ""
    document_metadata: dict = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.chunks)


class TextChunker:
    """文本分块器"""

    # 分块分隔符优先级 (递归字符分块)
    SEPARATORS = [
        "\n\n\n",  # 段落间多空行
        "\n\n",    # 段落
        "\n",      # 行
        "。",      # 中文句号
        "！",      # 中文感叹号
        "？",      # 中文问号
        ". ",      # 英文句号
        "! ",
        "? ",
        "；",      # 中文分号
        "; ",      # 英文分号
        "，",      # 中文逗号
        ", ",      # 英文逗号
        " ",       # 空格
        "",        # 字符级
    ]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: ParsedDocument) -> ChunkResult:
        """对整个文档进行分块

        Args:
            doc: 解析后的文档

        Returns:
            ChunkResult: 分块结果
        """
        all_chunks: list[Chunk] = []
        chunk_idx = 0

        for page_info in doc.pages:
            page_num = page_info.get("page", 1)
            text = page_info.get("text", "")
            tables = page_info.get("tables", [])

            if not text.strip():
                continue

            # 识别文本中的表格区域，将其整体作为一个分块
            table_patterns = [r"\[表格\]\n(.*?)(?=\n\[|\Z)", r"\[图片OCR\]\n(.*?)(?=\n\[|\Z)"]

            # 将表格区域提取出来单独分块
            text_parts, extracted_special = self._extract_special_blocks(text)

            # 对纯文本部分进行递归分块
            for part in text_parts:
                if not part.strip():
                    continue
                sub_chunks = self._recursive_split(part)
                for sc in sub_chunks:
                    all_chunks.append(Chunk(
                        content=sc,
                        chunk_type="text",
                        chunk_index=chunk_idx,
                        page=page_num,
                        metadata={"source_page": page_num},
                    ))
                    chunk_idx += 1

            # 表格作为整体分块
            for table_md in tables:
                if table_md.strip():
                    all_chunks.append(Chunk(
                        content=table_md,
                        chunk_type="table",
                        chunk_index=chunk_idx,
                        page=page_num,
                        metadata={"source_page": page_num, "is_table": True},
                    ))
                    chunk_idx += 1

            # OCR 文本分块
            for img_text in page_info.get("images", []):
                if img_text.strip():
                    sub_chunks = self._recursive_split(img_text)
                    for sc in sub_chunks:
                        all_chunks.append(Chunk(
                            content=sc,
                            chunk_type="image_caption",
                            chunk_index=chunk_idx,
                            page=page_num,
                            metadata={"source_page": page_num, "is_ocr": True},
                        ))
                        chunk_idx += 1

        result = ChunkResult(
            chunks=all_chunks,
            document_title=doc.title,
            document_metadata=doc.metadata,
        )

        log.info(
            f"分块完成: {result.document_title}, "
            f"总分块数={result.count}, "
            f"chunk_size={self.chunk_size}, overlap={self.chunk_overlap}"
        )
        return result

    def _extract_special_blocks(self, text: str) -> tuple[list[str], list[str]]:
        """提取特殊块(表格/OCR)，返回剩余文本部分和特殊块"""
        special_blocks = []
        remaining_parts = []

        # 按 [表格] 和 [图片OCR] 标记分割
        pattern = r"(\[表格\]|\[图片OCR\])"
        parts = re.split(pattern, text)

        current_text = []
        for i, part in enumerate(parts):
            if part in ("[表格]", "[图片OCR]"):
                # 保存之前的文本
                if current_text:
                    remaining_parts.append("".join(current_text))
                    current_text = []
                # 收集标记后的内容直到下一个标记
                if i + 1 < len(parts):
                    special_blocks.append(f"{part}\n{parts[i + 1]}")
            else:
                if part.strip():
                    current_text.append(part)

        if current_text:
            remaining_parts.append("".join(current_text))

        return remaining_parts, special_blocks

    def _recursive_split(
        self, text: str, separators: Optional[list[str]] = None
    ) -> list[str]:
        """递归字符分块 - 按优先级使用不同分隔符"""
        separators = separators or self.SEPARATORS
        chunks = []

        if len(text) <= self.chunk_size:
            if text.strip():
                chunks.append(text.strip())
            return chunks

        # 找到第一个有效的分隔符
        sep = ""
        for s in separators:
            if s == "":
                sep = ""
                break
            if s in text:
                sep = s
                break

        if sep == "":
            # 字符级切分
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i : i + self.chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
                if i + self.chunk_size >= len(text):
                    break
            return chunks

        # 按分隔符切分
        splits = text.split(sep)
        current_chunk = ""

        for split in splits:
            candidate = current_chunk + sep + split if current_chunk else split
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # 如果单个 split 超过 chunk_size，递归切分
                if len(split) > self.chunk_size:
                    sub_chunks = self._recursive_split(split, separators[separators.index(sep) + 1:] if sep in separators else None)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 添加重叠
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """为分块添加重叠部分"""
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-self.chunk_overlap :] if len(chunks[i - 1]) > self.chunk_overlap else chunks[i - 1]
            overlapped.append(prev_tail + chunks[i])
        return overlapped

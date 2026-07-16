"""
文档服务公共类型定义
提取到独立模块以避免 loader ↔ parser 循环导入
"""

from dataclasses import dataclass, field


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

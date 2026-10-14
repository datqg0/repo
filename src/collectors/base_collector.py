# src/collectors/base_collector.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class RawJob(BaseModel):
    """Data Transfer Object (DTO) chuẩn hóa bài đăng từ mọi nguồn."""
    raw_id: str = Field(description="ID định danh duy nhất (vd: li_12345, fb_98765)")
    source: str = Field(description="Nguồn: 'linkedin', 'facebook_group', 'itviec'...")
    source_name: str = Field(default="", description="Tên nhóm hoặc chuyên mục")
    author_name: str = Field(default="", description="Tên người đăng hoặc công ty")
    raw_text: str = Field(description="Nội dung thô của bài tuyển dụng")
    url: str = Field(description="Link trực tiếp tới bài đăng gốc")
    posted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Thời điểm đăng bài (ISO string)")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class BaseCollector(ABC):
    """Lớp cơ sở cho các module thu thập tin tuyển dụng."""

    @abstractmethod
    def collect(self) -> List[RawJob]:
        """Thu thập danh sách RawJob từ nguồn mục tiêu."""
        pass

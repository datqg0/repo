# src/pipeline/pre_filter.py
import re
import hashlib
from typing import Tuple

try:
    from src.config import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS
except ImportError:
    from config import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS

def compute_content_hash(text: str) -> str:
    """
    Chuẩn hóa văn bản bài viết để băm MD5 chống trùng chéo:
    - Chuyển chữ thường
    - Xóa các dãy số (ngày tháng, số điện thoại, mức lương thay đổi nhỏ)
    - Xóa dấu câu, icon và ký tự đặc biệt
    - Gộp khoảng trắng thừa
    - Lấy 300 ký tự cốt lõi đầu tiên để sinh mã băm
    """
    if not text:
        return ""
    clean = text.lower()
    clean = re.sub(r'\d+', '', clean)            # Xóa số để bắt các bài đăng lại đổi hotline/ngày
    clean = re.sub(r'[^\w\s]', '', clean)        # Xóa dấu câu, emoji
    clean = re.sub(r'\s+', ' ', clean).strip()   # Gộp khoảng trắng
    core_sample = clean[:300]
    return hashlib.md5(core_sample.encode("utf-8")).hexdigest()

def passes_keyword_filter(text: str) -> Tuple[bool, str]:
    """
    Kiểm tra nhanh xem bài viết có vượt qua bộ lọc từ khóa hay không:
    - Độ dài tối thiểu 60 ký tự
    - Không dính từ khóa cấm (ứng viên tìm việc, khóa học lừa đảo, ctv bán hàng)
    - Phải chứa ít nhất 1 từ khóa tích cực tuyển dụng/kỹ thuật
    """
    if not text or len(text.strip()) < 60:
        return False, "Bài viết quá ngắn (< 60 ký tự)"

    lower_text = text.lower()

    # 1. Dính từ khóa loại trừ -> Loại bỏ ngay
    for neg in NEGATIVE_KEYWORDS:
        if neg in lower_text:
            return False, f"Chứa từ khóa loại trừ: '{neg}'"

    # 2. Phải chứa ít nhất 1 từ khóa mục tiêu
    if not any(pos in lower_text for pos in POSITIVE_KEYWORDS):
        return False, "Không chứa từ khóa tuyển dụng/công nghệ mục tiêu"

    return True, "OK"

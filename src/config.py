# src/config.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Đảm bảo in ký tự tiếng Việt UTF-8 mượt mà trên console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Tìm và nạp file .env từ thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# 1. API Keys & Tích hợp dịch vụ bên ngoài
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

# 2. Cấu hình cào LinkedIn
LINKEDIN_KEYWORDS = [
    "Unity Developer",
    "Game Developer",
    "C# Developer",
    "C++ Developer",
    "Node.js Developer",
    "Java Backend",
    "Backend Developer",
    "Fresher IT",
]
LINKEDIN_LOCATION = os.getenv("LINKEDIN_LOCATION", "Hanoi, Vietnam")

# 3. Cấu hình cào Facebook Groups
# Lưu ý: Luôn giữ đuôi ?sorting_setting=CHRONOLOGICAL để ép Facebook xếp bài mới nhất lên đầu
FB_GROUP_URLS = [
    "https://www.facebook.com/groups/congdongunityvietnam/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/gamedevvietnam/?sorting_setting=CHRONOLOGICAL",
]

# 4. Bộ từ khóa lọc thô (Chạy siêu tốc 0.1ms trước khi gọi AI)
NEGATIVE_KEYWORDS = [
    "tìm việc", "xin thực tập", "em đang tìm", "nhận làm đồ án", 
    "khóa học", "cam kết đầu ra", "học viên", "việc nhẹ lương cao",
    "tuyển cộng tác viên bán hàng", "tuyển ctv bán hàng", "tuyển mẫu ảnh",
    "tuyển dụng ctv", "đầu tư", "hoa hồng", "tiếp thị liên kết"
]

POSITIVE_KEYWORDS = [
    "tuyển", "hiring", "jd", "cần tìm", "developer", "lập trình",
    "unity", "game", "c#", "c++", "java", "node", "backend", "fullstack",
    "intern", "fresher", "junior", "thực tập", "dev"
]

# 5. Ngưỡng điểm chất lượng (0 - 100)
MIN_SCORE_NOTIFY = int(os.getenv("MIN_SCORE_NOTIFY", 70))  # >= 70 điểm: Gửi Telegram & tab Cần Nộp Ngay
MIN_SCORE_BACKUP = int(os.getenv("MIN_SCORE_BACKUP", 50))  # 50 - 69 điểm: Lưu tab Dự Phòng

# 6. Cấu hình Chrome Remote Debugging
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", 9222))
CDP_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"
CHROME_PROFILE_DIR = ROOT_DIR / "chrome_profile"

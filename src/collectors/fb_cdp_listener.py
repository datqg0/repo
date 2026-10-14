# src/collectors/fb_cdp_listener.py
import json
import time
import random
import socket
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

try:
    from src.config import FB_GROUP_URLS, CDP_URL, CHROME_DEBUG_PORT
    from src.collectors.base_collector import BaseCollector, RawJob
except ImportError:
    from config import FB_GROUP_URLS, CDP_URL, CHROME_DEBUG_PORT
    from collectors.base_collector import BaseCollector, RawJob

def is_cdp_available(host: str = "127.0.0.1", port: int = 9222) -> bool:
    """Kiểm tra xem Chrome Remote Debugging có đang mở trên cổng chỉ định hay không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def extract_posts_from_json(obj: Any, found_posts: Dict[str, dict], group_url: str = ""):
    """
    Đệ quy tìm các node bài viết (Story / Feed Unit) bên trong dữ liệu GraphQL của Facebook.
    Tự động trích xuất post_id, nội dung văn bản và link bài viết.
    """
    if isinstance(obj, dict):
        post_id = obj.get("post_id") or obj.get("id")
        message = obj.get("message")
        
        # Một bài đăng Facebook thường có post_id và text nằm ở message.text
        if post_id and isinstance(message, dict) and message.get("text"):
            text = str(message["text"]).strip()
            # Lấy URL của bài viết nếu có, hoặc tạo URL theo post_id
            post_url = obj.get("url") or f"https://www.facebook.com/{post_id}"
            
            # Chỉ nhận bài đăng có độ dài tối thiểu 60 ký tự
            if len(text) >= 60:
                raw_id = f"fb_{post_id}"
                if raw_id not in found_posts:
                    found_posts[raw_id] = {
                        "raw_id": raw_id,
                        "source": "facebook_group",
                        "source_name": group_url.split("/groups/")[1].split("/")[0] if "/groups/" in group_url else "Facebook Group",
                        "author_name": obj.get("actors", [{}])[0].get("name", "") if isinstance(obj.get("actors"), list) and obj.get("actors") else "",
                        "raw_text": text,
                        "url": post_url
                    }
        
        # Tiếp tục đệ quy qua tất cả các value trong dictionary
        for val in obj.values():
            extract_posts_from_json(val, found_posts, group_url)

    elif isinstance(obj, list):
        for item in obj:
            extract_posts_from_json(item, found_posts, group_url)

class FacebookCDPCollector(BaseCollector):
    """Collector thu hoạch tin tuyển dụng Facebook Group bằng cách bắt gói tin ngầm GraphQL qua Chrome CDP."""

    def __init__(self, group_urls: List[str] = None):
        self.group_urls = group_urls or FB_GROUP_URLS

    def collect(self) -> List[RawJob]:
        return fetch_facebook_group_jobs(group_urls=self.group_urls)

def fetch_facebook_group_jobs(group_urls: List[str] = None) -> List[dict]:
    """
    Nối vào cửa sổ Chrome thật qua cổng 9222, cuộn qua các Group và bắt gói tin GraphQL.
    """
    urls = group_urls or FB_GROUP_URLS
    found_posts: Dict[str, dict] = {}

    # 1. Kiểm tra cổng CDP
    if not is_cdp_available("127.0.0.1", CHROME_DEBUG_PORT):
        print(f"[Facebook] ⚠️ Chưa bật Chrome Debugging ở cổng {CHROME_DEBUG_PORT}.")
        print("  -> Vui lòng nhấp đúp chạy file 'start_chrome_debug.bat' trước để cào Facebook.")
        return []

    current_group_url = ""

    def handle_response(response):
        nonlocal current_group_url
        if "/api/graphql/" in response.url and response.status == 200:
            try:
                raw_body = response.text()
                # Facebook thường trả về Newline Delimited JSON (nhiều object JSON trên các dòng)
                for line in raw_body.splitlines():
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            data = json.loads(line)
                            extract_posts_from_json(data, found_posts, current_group_url)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass

    try:
        with sync_playwright() as p:
            print(f"[Facebook] Đang kết nối vào Chrome thật qua {CDP_URL}...")
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.on("response", handle_response)

            for group_url in urls:
                current_group_url = group_url
                # Đảm bảo có tham số ?sorting_setting=CHRONOLOGICAL
                target_url = group_url
                if "sorting_setting=CHRONOLOGICAL" not in target_url:
                    target_url += "&sorting_setting=CHRONOLOGICAL" if "?" in target_url else "?sorting_setting=CHRONOLOGICAL"

                print(f"[Facebook] Đang mở nhóm: {target_url}")
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as ge:
                    print(f"  -> Cảnh báo tải trang: {ge}")

                time.sleep(random.uniform(4.0, 6.0))

                # Cuộn trang 5-6 lần mô phỏng hành vi người thật
                for step in range(5):
                    scroll_y = random.randint(700, 1100)
                    page.mouse.wheel(0, scroll_y)
                    print(f"  -> Cuộn lần {step + 1}/5 (xuống {scroll_y}px), đang đón gói tin GraphQL...")
                    time.sleep(random.uniform(3.5, 7.5))

                # Nghỉ giãn cách giữa các nhóm tránh checkpoint
                wait_between = random.uniform(8.0, 12.0)
                print(f"  -> Tạm nghỉ {wait_between:.1f}s trước nhóm tiếp theo...")
                time.sleep(wait_between)

            page.close()

    except Exception as e:
        print(f"[Facebook] Lỗi khi kết nối hoặc cuộn Chrome CDP: {e}")

    print(f"[Facebook] Thu hoạch được {len(found_posts)} bài viết từ gói tin ngầm.")
    return list(found_posts.values())

if __name__ == "__main__":
    jobs = fetch_facebook_group_jobs()
    print(f"Test Facebook collector: {len(jobs)} bài.")

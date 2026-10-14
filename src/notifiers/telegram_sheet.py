# src/notifiers/telegram_sheet.py
import httpx
from typing import Dict, Any

try:
    from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GOOGLE_SHEET_WEBHOOK, MIN_SCORE_NOTIFY, MIN_SCORE_BACKUP
except ImportError:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GOOGLE_SHEET_WEBHOOK, MIN_SCORE_NOTIFY, MIN_SCORE_BACKUP

def send_telegram_alert(job: Dict[str, Any], ai_result: Dict[str, Any]):
    """
    Gửi tin nhắn định dạng HTML về Telegram Bot.
    Nếu chưa cấu hình Token thì tự động in thông báo nổi bật ra Terminal Console.
    """
    total_score = ai_result.get("total_score", 0)
    role_title = ai_result.get("role_title", "Vị trí tuyển dụng")
    company_name = ai_result.get("company_name", "Ẩn danh")
    seniority = ai_result.get("seniority_level", "Không xác định")
    tech_stack = ", ".join(ai_result.get("tech_stack", [])) or "Không rõ"
    salary = ai_result.get("salary_info", "Thỏa thuận")
    location = ai_result.get("work_location", "Không rõ")
    contact = ai_result.get("contact_method", "Xem bài viết gốc")
    summary = ai_result.get("one_line_summary", "")
    url = job.get("url", "")
    source = job.get("source", "Web")

    # In ra Terminal Console
    print("\n" + "=" * 60)
    print(f"🔥 [CHẤT LƯỢNG CAO {total_score}/100 ĐIỂM] {role_title}")
    print(f"🏢 Công ty: {company_name} | 📍 Địa điểm: {location}")
    print(f"🎯 Cấp bậc: {seniority} | 💰 Lương: {salary}")
    print(f"🛠 Công nghệ: {tech_stack}")
    print(f"💡 Nhận xét: {summary}")
    print(f"🔗 Link bài: {url}")
    print("=" * 60 + "\n")

    # Nếu chưa điền Token thì dừng, chỉ xem trên Console
    if not TELEGRAM_BOT_TOKEN or "DIEN_TELEGRAM" in TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Notifier] ℹ️ Chưa cấu hình Telegram Bot Token hoặc Chat ID, đã hiển thị lên Console.")
        return

    msg = (
        f"🔥 <b>[{total_score}/100 điểm] {role_title}</b>\n"
        f"🏢 <b>Công ty:</b> {company_name}\n"
        f"🎯 <b>Cấp bậc:</b> {seniority}\n"
        f"🛠 <b>Công nghệ:</b> {tech_stack}\n"
        f"💰 <b>Mức lương:</b> {salary}\n"
        f"📍 <b>Địa điểm:</b> {location}\n"
        f"📬 <b>Liên hệ:</b> {contact}\n\n"
        f"💡 <i>{summary}</i>\n"
        f"🔗 <a href='{url}'>Xem bài đăng gốc ({source})</a>"
    )

    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(telegram_api_url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            })
            if resp.status_code == 200:
                print(f"[Notifier] ✅ Đã gửi tin việc làm '{role_title}' tới Telegram thành công.")
            else:
                print(f"[Notifier] ⚠️ Lỗi gửi Telegram: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[Notifier] ⚠️ Không kết nối được tới Telegram API: {e}")

def sync_to_google_sheet(job: Dict[str, Any], ai_result: Dict[str, Any], sheet_tab: str):
    """
    Gửi dữ liệu việc làm lên Google Sheets thông qua Webhook Google Apps Script.
    """
    if not GOOGLE_SHEET_WEBHOOK:
        return

    payload = {
        "tab": sheet_tab,
        "raw_id": job.get("raw_id", ""),
        "source": job.get("source", ""),
        "company": ai_result.get("company_name", ""),
        "role_title": ai_result.get("role_title", ""),
        "seniority": ai_result.get("seniority_level", ""),
        "tech_stack": ", ".join(ai_result.get("tech_stack", [])),
        "salary": ai_result.get("salary_info", ""),
        "location": ai_result.get("work_location", ""),
        "score": ai_result.get("total_score", 0),
        "summary": ai_result.get("one_line_summary", ""),
        "url": job.get("url", "")
    }

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.post(GOOGLE_SHEET_WEBHOOK, json=payload)
            if resp.status_code == 200:
                print(f"[Google Sheet] ✅ Đã đồng bộ bài lên tab '{sheet_tab}'.")
    except Exception as e:
        print(f"[Google Sheet] ⚠️ Lỗi đồng bộ Google Sheets: {e}")

def notify_and_sync(job: Dict[str, Any], ai_result: Dict[str, Any]):
    """
    Điều phối thông báo theo thang điểm chuẩn trong Plan.md:
    - Điểm >= 70: Bắn Telegram + Ghi vào tab 'Cần Nộp Ngay' trên Google Sheets
    - Điểm 50 - 69: Ghi vào tab 'Dự Phòng' trên Google Sheets
    - Điểm < 50: Không gửi thông báo
    """
    score = ai_result.get("total_score", 0)

    if score >= MIN_SCORE_NOTIFY:
        send_telegram_alert(job, ai_result)
        sync_to_google_sheet(job, ai_result, sheet_tab="Cần Nộp Ngay")
    elif score >= MIN_SCORE_BACKUP:
        print(f"[Notifier] 📋 Lưu dự phòng ({score}/100đ): {ai_result.get('role_title')} ({ai_result.get('company_name')})")
        sync_to_google_sheet(job, ai_result, sheet_tab="Dự Phòng")
    else:
        # Điểm thấp dưới 50
        pass

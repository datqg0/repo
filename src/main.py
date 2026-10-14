# src/main.py
import sys
import time
import argparse
from pathlib import Path

# Đảm bảo console Windows hỗ trợ hiển thị tiếng Việt UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm thư mục src và thư mục gốc vào sys.path để import linh hoạt
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import MIN_SCORE_NOTIFY, MIN_SCORE_BACKUP, GEMINI_API_KEY
from db import init_db, is_duplicate_or_repost, save_job, get_job_stats
from pre_filter import compute_content_hash, passes_keyword_filter
from linkedin_api import fetch_linkedin_jobs
from fb_cdp_listener import fetch_facebook_group_jobs
from ai_scorer import evaluate_job_with_ai
from notifier import notify_and_sync, send_telegram_alert

def run_pipeline(source: str = "all", dry_run: bool = False):
    """Điều phối toàn bộ quy trình thu thập, lọc, chấm điểm và thông báo."""
    print("=" * 65)
    print("🚀  JOBHUNTER BOT — BẮT ĐẦU CHU KỲ QUÉT & CHẤM ĐIỂM VIỆC LÀM")
    print("=" * 65)
    
    init_db()

    # 1. Thu thập dữ liệu thô
    raw_jobs = []
    
    if source in ("all", "linkedin"):
        print("\n[BƯỚC 1/5] Thu thập dữ liệu từ LinkedIn Guest API...")
        try:
            li_jobs = fetch_linkedin_jobs()
            raw_jobs.extend(li_jobs)
        except Exception as e:
            print(f"[LinkedIn] ⚠️ Lỗi thu thập: {e}")

    if source in ("all", "facebook"):
        print("\n[BƯỚC 1/5] Thu thập dữ liệu từ Facebook Group qua Chrome CDP...")
        try:
            fb_jobs = fetch_facebook_group_jobs()
            raw_jobs.extend(fb_jobs)
        except Exception as e:
            print(f"[Facebook] ⚠️ Lỗi thu thập: {e}")

    print(f"\n[BƯỚC 2/5] Tổng hợp thu được {len(raw_jobs)} bài đăng thô.")
    if not raw_jobs:
        print("[!] Không có bài đăng mới nào để xử lý. Kết thúc chu kỳ.")
        return

    # Bộ đếm thống kê
    stats = {
        "total": len(raw_jobs),
        "duplicate_skipped": 0,
        "keyword_rejected": 0,
        "ai_evaluated": 0,
        "not_a_job": 0,
        "qualified_notified": 0,
        "saved_backup": 0,
        "low_score": 0
    }

    print("\n[BƯỚC 3/5 & 4/5] Bắt đầu lọc trùng lặp, lọc từ khóa và chấm điểm AI...")

    for idx, job in enumerate(raw_jobs, 1):
        raw_id = job.get("raw_id", "")
        raw_text = job.get("raw_text", "")
        job_source = job.get("source", "")
        url = job.get("url", "")

        content_hash = compute_content_hash(raw_text)

        # 2. Kiểm tra trùng lặp SQLite (0ms, 0 token)
        if is_duplicate_or_repost(raw_id, content_hash):
            stats["duplicate_skipped"] += 1
            continue

        # 3. Lọc từ khóa loại trừ và mục tiêu (0.1ms)
        passed, reason = passes_keyword_filter(raw_text)
        if not passed:
            stats["keyword_rejected"] += 1
            if not dry_run:
                save_job({
                    "raw_id": raw_id,
                    "content_hash": content_hash,
                    "source": job_source,
                    "source_name": job.get("source_name", ""),
                    "url": url,
                    "status": "rejected_keyword"
                })
            continue

        # 4. Gọi Gemini API chấm điểm chất lượng
        print(f"\n[{idx}/{len(raw_jobs)}] 🧠 Đang gọi AI chấm điểm: {raw_id} ({job_source})...")
        stats["ai_evaluated"] += 1
        
        ai_res = evaluate_job_with_ai(raw_text)
        time.sleep(2.0)  # Giãn cách 2s để an toàn với hạn mức miễn phí của Gemini

        if not ai_res or not ai_res.get("is_valid_job"):
            stats["not_a_job"] += 1
            print(f"  -> Bỏ qua: Không phải tin tuyển dụng hợp lệ.")
            if not dry_run:
                save_job({
                    "raw_id": raw_id,
                    "content_hash": content_hash,
                    "source": job_source,
                    "source_name": job.get("source_name", ""),
                    "url": url,
                    "status": "not_a_job"
                })
            continue

        score = ai_res.get("total_score", 0)
        role = ai_res.get("role_title", "")
        company = ai_res.get("company_name", "")

        # Phân loại trạng thái theo điểm
        if score >= MIN_SCORE_NOTIFY:
            status = "notified"
            stats["qualified_notified"] += 1
            print(f"  -> ⭐ ĐẠT CHUẨN XUẤT SẮC ({score}/100đ): {role} tại {company}")
        elif score >= MIN_SCORE_BACKUP:
            status = "saved_backup"
            stats["saved_backup"] += 1
            print(f"  -> 📋 ĐẠT MỨC DỰ PHÒNG ({score}/100đ): {role} tại {company}")
        else:
            status = "low_score"
            stats["low_score"] += 1
            print(f"  -> 📉 ĐIỂM THẤP ({score}/100đ): {role} tại {company}")

        # 5. Lưu vào SQLite
        if not dry_run:
            save_job({
                "raw_id": raw_id,
                "content_hash": content_hash,
                "source": job_source,
                "source_name": job.get("source_name", ""),
                "company": company,
                "role_title": role,
                "seniority_level": ai_res.get("seniority_level", ""),
                "tech_stack": ", ".join(ai_res.get("tech_stack", [])),
                "salary_info": ai_res.get("salary_info", ""),
                "ai_score": score,
                "url": url,
                "status": status
            })

        # 6. Gửi thông báo Telegram & đồng bộ Google Sheets
        notify_and_sync(job, ai_res)

    # In báo cáo tổng kết
    print("\n" + "=" * 65)
    print("📊  BÁO CÁO TỔNG KẾT CHU KỲ")
    print("=" * 65)
    print(f"• Tổng bài đăng quét được:          {stats['total']}")
    print(f"• Bài trùng lặp (đã bỏ qua):         {stats['duplicate_skipped']}")
    print(f"• Bài loại do bộ lọc từ khóa:        {stats['keyword_rejected']}")
    print(f"• Bài được chuyển tới AI chấm điểm:  {stats['ai_evaluated']}")
    print(f"• Bài không phải tin tuyển dụng:     {stats['not_a_job']}")
    print(f"• 🌟 Tin tuyển dụng ĐẠT (>= 70đ):    {stats['qualified_notified']}")
    print(f"• 📋 Tin dự phòng (50 - 69đ):        {stats['saved_backup']}")
    print(f"• 📉 Tin điểm thấp (< 50đ):          {stats['low_score']}")
    print("=" * 65 + "\n")

def test_ai_connection():
    """Kiểm tra kết nối và cấu hình Gemini API."""
    print("[Kiểm tra AI] Đang kiểm tra kết nối Google Gemini API...")
    if not GEMINI_API_KEY or "DIEN_GEMINI" in GEMINI_API_KEY:
        print("[Kiểm tra AI] ❌ Lỗi: Bạn chưa điền GEMINI_API_KEY vào file .env!")
        return

    sample = (
        "Cần tuyển 01 Unity Game Developer (Junior) tại Cầu Giấy, Hà Nội. "
        "Lương 15 - 20 triệu VNĐ. Công ty TNHH Game Studio VN. "
        "Yêu cầu: 1 năm kinh nghiệm Unity C#, làm game mobile 2D/3D. "
        "Gửi CV về hr@gamestudiovn.com"
    )
    res = evaluate_job_with_ai(sample)
    if res:
        print("[Kiểm tra AI] ✅ Kết nối thành công! Kết quả phân tích mẫu:")
        for k, v in res.items():
            print(f"  • {k}: {v}")
    else:
        print("[Kiểm tra AI] ❌ Không nhận được phản hồi từ AI.")

def test_telegram_connection():
    """Kiểm tra gửi tin nhắn mẫu về Telegram."""
    sample_job = {
        "raw_id": "test_001",
        "source": "Kiểm tra hệ thống",
        "url": "https://example.com"
    }
    sample_ai = {
        "total_score": 95,
        "role_title": "Unity Game Developer (Fresher/Junior)",
        "company_name": "Antigravity Demo Studio",
        "seniority_level": "Fresher",
        "tech_stack": ["Unity", "C#", "SQL"],
        "salary_info": "15 - 18 triệu VNĐ",
        "work_location": "Hà Nội / Hybrid",
        "contact_method": "hr@antigravity.demo",
        "one_line_summary": "Studio game tuyển trực tiếp Unity Fresher lương tốt, minh bạch thông tin."
    }
    print("[Kiểm tra Telegram] Đang gửi tin nhắn mẫu...")
    send_telegram_alert(sample_job, sample_ai)

def show_database_stats():
    """Hiển thị số liệu thống kê trong SQLite."""
    init_db()
    stats = get_job_stats()
    print("\n" + "=" * 50)
    print("📊 THỐNG KÊ CƠ SỞ DỮ LIỆU SQLITE (jobs.db)")
    print("=" * 50)
    print(f"Tổng số bài viết đã lưu: {stats['total']}")
    print(f"Số bài đạt chất lượng cao (>= 70đ): {stats['high_score_count']}")
    print("\nTheo nguồn:")
    for src, cnt in stats["by_source"].items():
        print(f"  - {src}: {cnt}")
    print("\nTheo trạng thái:")
    for st, cnt in stats["by_status"].items():
        print(f"  - {st}: {cnt}")
    print("=" * 50 + "\n")

def main():
    parser = argparse.ArgumentParser(description="JobHunter Bot - Hệ thống săn việc làm tự động")
    parser.add_argument("--source", choices=["all", "linkedin", "facebook"], default="all",
                        help="Nguồn dữ liệu muốn cào: linkedin, facebook, hoặc all (mặc định: all)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm không lưu vào cơ sở dữ liệu")
    parser.add_argument("--test-ai", action="store_true", help="Kiểm tra kết nối Gemini API")
    parser.add_argument("--test-telegram", action="store_true", help="Gửi tin nhắn mẫu kiểm tra Telegram")
    parser.add_argument("--stats", action="store_true", help="Xem thống kê số lượng bài trong SQLite")

    args = parser.parse_args()

    if args.test_ai:
        test_ai_connection()
    elif args.test_telegram:
        test_telegram_connection()
    elif args.stats:
        show_database_stats()
    else:
        run_pipeline(source=args.source, dry_run=args.dry_run)

if __name__ == "__main__":
    main()

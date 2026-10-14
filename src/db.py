# src/db.py
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

def get_conn() -> sqlite3.Connection:
    """Tạo kết nối SQLite, tự động tạo thư mục data/ nếu chưa có."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo bảng jobs và các index tối ưu truy vấn."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                raw_id TEXT PRIMARY KEY,
                content_hash TEXT,
                source TEXT,
                source_name TEXT DEFAULT '',
                company TEXT DEFAULT '',
                role_title TEXT DEFAULT '',
                seniority_level TEXT DEFAULT '',
                tech_stack TEXT DEFAULT '',
                salary_info TEXT DEFAULT '',
                ai_score INTEGER DEFAULT 0,
                url TEXT,
                repost_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'new',
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON jobs(content_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status_score ON jobs(status, ai_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)")

def is_duplicate_or_repost(raw_id: str, content_hash: str) -> bool:
    """
    Kiểm tra bài viết đã từng quét chưa (theo ID gốc hoặc theo băm nội dung).
    Nếu trùng nội dung: Tăng repost_count và cập nhật last_seen_at.
    Phát hiện Ghost Job nếu đăng lại >= 4 lần sau 30 ngày.
    """
    with get_conn() as conn:
        # 1. Kiểm tra ID gốc (trùng bài viết tuyệt đối)
        if raw_id:
            row = conn.execute("SELECT 1 FROM jobs WHERE raw_id = ?", (raw_id,)).fetchone()
            if row:
                return True

        # 2. Kiểm tra mã băm nội dung (HR đăng lại cùng 1 nội dung ở group khác hoặc thời điểm khác)
        if content_hash:
            hash_row = conn.execute(
                "SELECT raw_id, repost_count, first_seen_at FROM jobs WHERE content_hash = ?", 
                (content_hash,)
            ).fetchone()
            if hash_row:
                current_repost = hash_row["repost_count"] or 1
                new_repost = current_repost + 1
                
                # Kiểm tra Ghost Job (đăng lại nhiều lần trong thời gian dài)
                new_status = None
                try:
                    first_seen = datetime.fromisoformat(str(hash_row["first_seen_at"]).replace(" ", "T"))
                    days_active = (datetime.utcnow() - first_seen).days
                    if new_repost >= 4 and days_active >= 30:
                        new_status = "ghost_job"
                except Exception:
                    pass

                if new_status:
                    conn.execute("""
                        UPDATE jobs 
                        SET repost_count = ?, last_seen_at = CURRENT_TIMESTAMP, status = ?
                        WHERE content_hash = ?
                    """, (new_repost, new_status, content_hash))
                else:
                    conn.execute("""
                        UPDATE jobs 
                        SET repost_count = ?, last_seen_at = CURRENT_TIMESTAMP
                        WHERE content_hash = ?
                    """, (new_repost, content_hash))
                return True

    return False

def save_job(job_data: Dict[str, Any]):
    """Lưu hoặc cập nhật bài viết vào cơ sở dữ liệu SQLite."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO jobs 
            (raw_id, content_hash, source, source_name, company, role_title, seniority_level, 
             tech_stack, salary_info, ai_score, url, repost_count, status, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(raw_id) DO UPDATE SET
                content_hash = excluded.content_hash,
                source = excluded.source,
                source_name = COALESCE(excluded.source_name, jobs.source_name),
                company = COALESCE(NULLIF(excluded.company, ''), jobs.company),
                role_title = COALESCE(NULLIF(excluded.role_title, ''), jobs.role_title),
                seniority_level = COALESCE(NULLIF(excluded.seniority_level, ''), jobs.seniority_level),
                tech_stack = COALESCE(NULLIF(excluded.tech_stack, ''), jobs.tech_stack),
                salary_info = COALESCE(NULLIF(excluded.salary_info, ''), jobs.salary_info),
                ai_score = excluded.ai_score,
                url = excluded.url,
                status = excluded.status,
                last_seen_at = CURRENT_TIMESTAMP
        """, (
            job_data["raw_id"],
            job_data.get("content_hash", ""),
            job_data.get("source", ""),
            job_data.get("source_name", ""),
            job_data.get("company", ""),
            job_data.get("role_title", ""),
            job_data.get("seniority_level", ""),
            job_data.get("tech_stack", ""),
            job_data.get("salary_info", ""),
            job_data.get("ai_score", 0),
            job_data.get("url", ""),
            job_data.get("repost_count", 1),
            job_data.get("status", "new")
        ))

def get_job_stats() -> Dict[str, Any]:
    """Lấy thống kê số lượng bài tuyển dụng theo trạng thái."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        status_rows = conn.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status").fetchall()
        source_rows = conn.execute("SELECT source, COUNT(*) as count FROM jobs GROUP BY source").fetchall()
        top_scored = conn.execute("SELECT COUNT(*) FROM jobs WHERE ai_score >= 70").fetchone()[0]
        
    return {
        "total": total,
        "high_score_count": top_scored,
        "by_status": {row["status"]: row["count"] for row in status_rows},
        "by_source": {row["source"]: row["count"] for row in source_rows}
    }

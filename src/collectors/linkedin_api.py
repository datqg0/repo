# src/collectors/linkedin_api.py
import time
import random
from typing import List, Set
import httpx
from bs4 import BeautifulSoup

try:
    from src.config import LINKEDIN_KEYWORDS, LINKEDIN_LOCATION
    from src.db import is_duplicate_or_repost
    from src.collectors.base_collector import BaseCollector, RawJob
except ImportError:
    from config import LINKEDIN_KEYWORDS, LINKEDIN_LOCATION
    from db import is_duplicate_or_repost
    from collectors.base_collector import BaseCollector, RawJob

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

class LinkedInCollector(BaseCollector):
    """Trình thu thập tin tuyển dụng từ LinkedIn Guest Jobs API (Không cần đăng nhập)."""

    def __init__(self, keywords: List[str] = None, location: str = None):
        self.keywords = keywords or LINKEDIN_KEYWORDS
        self.location = location or LINKEDIN_LOCATION

    def collect(self) -> List[RawJob]:
        return fetch_linkedin_jobs(keywords=self.keywords, location=self.location)

def fetch_linkedin_jobs(keywords: List[str] = None, location: str = None) -> List[dict]:
    """
    Gọi thẳng vào LinkedIn Guest Jobs API để lấy danh sách việc làm mới trong 24h qua.
    Trả về danh sách dict chuẩn RawJob.
    """
    kws = keywords or LINKEDIN_KEYWORDS
    loc = location or LINKEDIN_LOCATION
    collected_jobs: List[dict] = []
    seen_in_session: Set[str] = set()

    with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        for kw in kws:
            print(f"[LinkedIn] Đang quét từ khóa: '{kw}' tại '{loc}'...")
            search_url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={httpx.URL(kw)}&location={httpx.URL(loc)}"
                "&f_TPR=r86400&sortBy=DD&start=0"
            )
            try:
                resp = client.get(search_url)
                if resp.status_code != 200:
                    print(f"  -> HTTP {resp.status_code} khi tìm '{kw}'")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="base-card")
                if not cards:
                    cards = soup.find_all("li")

                count_for_kw = 0
                for card in cards:
                    urn = card.get("data-entity-urn", "")
                    if not urn or ":" not in urn:
                        # Thử lấy từ thẻ a
                        link_el = card.find("a", class_="base-card__full-link")
                        if link_el and "currentJobId=" in link_el.get("href", ""):
                            job_id = link_el["href"].split("currentJobId=")[1].split("&")[0]
                        else:
                            continue
                    else:
                        job_id = urn.split(":")[-1]

                    raw_id = f"li_{job_id}"

                    # Bỏ qua ngay nếu đã xử lý trong phiên này hoặc đã có trong SQLite
                    if raw_id in seen_in_session or is_duplicate_or_repost(raw_id, ""):
                        continue
                    seen_in_session.add(raw_id)

                    # Tạm nghỉ ngẫu nhiên tránh rate limit
                    time.sleep(random.uniform(1.2, 2.5))
                    detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                    
                    try:
                        detail_resp = client.get(detail_url)
                        if detail_resp.status_code != 200:
                            continue

                        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                        title_el = detail_soup.find("h2", class_="top-card-layout__title")
                        comp_el = detail_soup.find("a", class_="topcard__org-name-link")
                        if not comp_el:
                            comp_el = detail_soup.find("span", class_="topcard__flavor")
                        desc_el = detail_soup.find("div", class_="show-more-less-html__markup")

                        title = title_el.get_text(strip=True) if title_el else ""
                        company = comp_el.get_text(strip=True) if comp_el else "Ẩn danh"
                        desc = desc_el.get_text(separator="\n", strip=True) if desc_el else ""

                        if not title and not desc:
                            continue

                        full_text = f"Công ty: {company}\nVị trí: {title}\nMô tả:\n{desc}"
                        job_item = {
                            "raw_id": raw_id,
                            "source": "linkedin",
                            "source_name": "LinkedIn Guest API",
                            "author_name": company,
                            "raw_text": full_text,
                            "url": f"https://www.linkedin.com/jobs/view/{job_id}/"
                        }
                        collected_jobs.append(job_item)
                        count_for_kw += 1
                    except Exception as de:
                        print(f"  -> Lỗi lấy chi tiết job {job_id}: {de}")

                print(f"  -> Thu hoạch được {count_for_kw} tin mới cho từ khóa '{kw}'.")

            except Exception as e:
                print(f"[LinkedIn] Lỗi khi quét '{kw}': {e}")

    print(f"[LinkedIn] Tổng cộng thu thập được {len(collected_jobs)} bài mới.")
    return collected_jobs

if __name__ == "__main__":
    jobs = fetch_linkedin_jobs(keywords=["Unity Developer"])
    print(f"Test LinkedIn collector: tìm thấy {len(jobs)} bài.")
    for j in jobs[:2]:
        print(f" - [{j['raw_id']}] {j['url']}: {j['raw_text'][:100]}...")

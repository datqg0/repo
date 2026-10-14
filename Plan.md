# 🎯 JobHunter Bot — Tài liệu Thiết kế Hệ thống & Kế hoạch Triển khai

Hệ thống tự động thu thập, khử trùng lặp và chấm điểm tin tuyển dụng đa nền tảng (Facebook Groups, LinkedIn, Job Boards) dành cho nhu cầu săn việc cá nhân. Thiết kế tối ưu để chạy nhẹ trên máy cá nhân, chi phí vận hành bằng 0 và chống khóa tài khoản (Anti-Checkpoint).

---

## 1. Kiến trúc Tổng quan & Nguyên lý Hoạt động

Thay vì dùng Selenium cạo thẻ HTML (DOM Scraping) truyền thống dễ gãy code và khóa nick, hệ thống hoạt động theo mô hình **Multi-Source Funnel (Phễu đa nguồn)** qua 5 tầng:

1. **Collectors (Thu thập):**
   - **LinkedIn:** Gọi thẳng HTTP `GET` vào *LinkedIn Guest Jobs API* (không cần đăng nhập, không cần mở trình duyệt).
   - **Facebook Groups:** Mở trình duyệt Chrome thật (lưu sẵn profile phụ) qua cổng Debug `9222`, dùng Playwright/Selenium tự cuộn trang và **bắt gói tin ngầm `/api/graphql/`** trả về ở tab Network.
2. **Normalizer (Chuẩn hóa):** Đưa dữ liệu thô từ mọi nguồn về chung một cấu trúc `RawJob`.
3. **Pre-Filter & Deduplication (Lọc thô & Chống trùng):** Kiểm tra `raw_id` trong SQLite, lọc từ khóa cấm bằng Regex và băm nội dung (`SimHash`/`MD5`) để chặn các bài HR đăng lại ở nhiều nhóm hoặc tin tuyển dụng ảo (Ghost Jobs).
4. **AI Scoring Engine (Chấm điểm chất lượng):** Gọi `gemini-2.5-flash` kèm JSON Schema cố định để trích xuất thông tin và chấm điểm bài đăng trên thang 100.
5. **Notifier & Tracker (Thông báo & Quản lý):** Bài đạt từ **70/100 điểm** trở lên được đẩy tức thì về **Telegram Bot** và ghi vào **Google Sheets**.

---

## 2. Tech Stack

| Thành phần | Lựa chọn 1: Python (Khuyên dùng) | Lựa chọn 2: Node.js | Vai trò |
| :--- | :--- | :--- | :--- |
| **Điều khiển Chrome & Bắt gói tin** | `playwright` (kết nối CDP cổng `9222`) | `playwright-core` | Cuộn Facebook Group trên Chrome thật và bắt gói JSON `/api/graphql/` |
| **Gọi API trực tiếp** | `curl_cffi` hoặc `httpx` + `BeautifulSoup4` | `undici` / `axios` + `cheerio` | Quét nhanh LinkedIn Guest API mà không cần mở trình duyệt |
| **Cơ sở dữ liệu nội bộ** | `sqlite3` (tích hợp sẵn) | `better-sqlite3` | Lưu lịch sử bài quét, chống trùng lặp và đếm số lần đăng lại |
| **Chấm điểm & Bóc tách bằng AI** | `google-genai` (`gemini-2.5-flash`) | `@google/genai` (`gemini-2.5-flash`) | Phân loại tin tuyển dụng, trả về Structured JSON và chấm điểm 0–100 |
| **Thông báo & Theo dõi** | Telegram Bot API + Google Apps Script | Telegram Bot API + Webhook | Bắn thông báo việc làm về điện thoại và ghi vào Google Sheets |
| **Lập lịch tự động** | Windows Task Scheduler / `APScheduler` | `node-cron` / Task Scheduler | Tự động chạy bot vào 3 khung giờ mỗi ngày kèm độ trễ ngẫu nhiên |

---

## 3. Cấu trúc Thư mục Dự án

```text
job-hunter-bot/
├── chrome_profile/              # Thư mục lưu Profile Chrome phụ (tự tạo khi chạy script mở Chrome)
├── data/
│   └── jobs.db                  # File cơ sở dữ liệu SQLite duy nhất
├── src/
│   ├── config.py                # Cấu hình API Key, danh sách URL Group FB, từ khóa và ngưỡng điểm
│   ├── db.py                    # Khởi tạo bảng SQLite, truy vấn chống trùng và cập nhật trạng thái
│   ├── collectors/
│   │   ├── base_collector.py    # Định nghĩa chuẩn đầu ra RawJob DTO
│   │   ├── linkedin_api.py      # Gọi thẳng LinkedIn Guest API bằng HTTP GET
│   │   └── fb_cdp_listener.py   # Nối vào Chrome cổng 9222, cuộn trang và bắt JSON GraphQL
│   ├── pipeline/
│   │   ├── pre_filter.py        # Lọc từ khóa cấm (Regex) + Băm văn bản chống trùng (SimHash/MD5)
│   │   └── ai_scorer.py         # Gọi Gemini API với JSON Schema để chấm điểm 0 - 100
│   └── notifiers/
│       └── telegram_sheet.py    # Đẩy tin nhắn về Telegram và bắn Webhook lên Google Sheets
├── start_chrome_debug.bat       # Script bật cửa sổ Chrome ở chế độ Remote Debugging (Port 9222)
├── main.py                      # Điểm chạy chính điều phối toàn bộ luồng dữ liệu
├── requirements.txt             # Danh sách thư viện cài đặt
└── ARCHITECTURE.md              # Tài liệu thiết kế hệ thống
```

---

## 4. Thiết kế Cơ sở Dữ liệu (`data/jobs.db`)

Chỉ sử dụng **1 bảng SQLite duy nhất** để tối ưu tốc độ truy vấn dưới 1 mili-giây:

```sql
CREATE TABLE IF NOT EXISTS jobs (
    raw_id TEXT PRIMARY KEY,          -- ID gốc (예: 'fb_123456' hoặc 'li_987654')
    content_hash TEXT,                -- Mã băm chuẩn hóa nội dung để chống trùng chéo giữa các Group/Web
    source TEXT,                      -- Nguồn: 'facebook_group', 'linkedin', 'itviec'
    source_name TEXT,                 -- Tên Group hoặc chuyên mục
    company TEXT,                     -- Tên công ty/studio (AI trích xuất)
    role_title TEXT,                  -- Vị trí tuyển dụng
    seniority_level TEXT,             -- Intern / Fresher / Junior / Middle
    tech_stack TEXT,                  -- Chuỗi công nghệ (VD: 'Unity, C#, 3D' hoặc 'Node.js, SQL')
    salary_info TEXT,                 -- Mức lương trích xuất từ bài viết
    ai_score INTEGER DEFAULT 0,       -- Điểm chất lượng tổng (0 - 100)
    url TEXT,                         -- Đường dẫn gốc tới bài đăng
    repost_count INTEGER DEFAULT 1,   -- Số lần bài viết này được đăng lại (phát hiện Ghost Job)
    status TEXT DEFAULT 'new',        -- 'rejected_keyword', 'low_score', 'saved_backup', 'notified', 'applied'
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON jobs(content_hash);
CREATE INDEX IF NOT EXISTS idx_status_score ON jobs(status, ai_score);
```

---

## 5. Thiết kế Chi tiết các Phân hệ

### 5.1. Chuẩn hóa Dữ liệu Đầu vào (`RawJob` DTO)
Mọi trình thu thập (`linkedin_api.py`, `fb_cdp_listener.py`) đều phải trả về danh sách các đối tượng theo mẫu:

```json
{
  "raw_id": "fb_12948192041",
  "source": "facebook_group",
  "source_name": "Cộng đồng Unity Việt Nam",
  "author_name": "Nguyen Van A",
  "raw_text": "Studio tại Cầu Giấy, Hà Nội cần tìm 02 bạn Unity Developer (Fresher/Junior)...",
  "url": "[https://www.facebook.com/groups/xxx/posts/12948192041/](https://www.facebook.com/groups/xxx/posts/12948192041/)",
  "posted_at": "2026-10-14T10:15:00Z"
}
```

### 5.2. Đặc tả Kỹ thuật Tầng Thu thập (Collectors)
* **LinkedIn Guest API (`linkedin_api.py`):**
  * **Endpoint danh sách:** `GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw}&location=Hanoi&f_TPR=r86400&sortBy=DD&start=0`
  * **Endpoint chi tiết JD:** `GET https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}`
  * **Chiến thuật mở rộng từ khóa (Query Expansion):** Lặp qua mảng từ khóa `["Unity Developer", "Game Developer", "C# Developer", "C++", "Backend Developer", "Node.js", "Java Spring", "Fresher IT"]`.
  * **Tối ưu:** Kiểm tra `li_{job_id}` trong SQLite trước khi gọi Endpoint chi tiết JD.

* **Facebook Group Interceptor (`fb_cdp_listener.py`):**
  * **Khởi chạy Chrome thật (`start_chrome_debug.bat`):**
    ```bat
    "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile"
    ```
  * **Ép thứ tự bài mới nhất:** Luôn truy cập URL Group có gắn tham số `?sorting_setting=CHRONOLOGICAL`.
  * **Cơ chế bắt dữ liệu:** Kết nối Playwright qua `connect_over_cdp("http://localhost:9222")`, lắng nghe sự kiện `page.on("response")` với các URL chứa `/api/graphql/`. Cuộn trang 5–7 lần với độ trễ ngẫu nhiên từ `3.5s` đến `8.0s` để thu hoạch các gói JSON chứa `story.message.text` và `post_id`.

### 5.3. Bộ lọc Thô & Chống trùng lặp (`pre_filter.py`)
1. **Kiểm tra ID gốc:** Nếu `raw_id` đã có trong bảng `jobs` -> Bỏ qua ngay (0ms).
2. **Lọc từ khóa loại trừ (`NEGATIVE_KEYWORDS`):**
   - Loại ngay nếu chứa: `["tìm việc", "xin thực tập", "em đang tìm", "nhận làm đồ án", "khóa học", "cam kết đầu ra", "tuyển ctv bán hàng", "việc nhẹ lương cao"]`.
3. **Lọc từ khóa mục tiêu (`POSITIVE_KEYWORDS`):**
   - Phải chứa ít nhất 1 từ trong nhóm tuyển dụng/kỹ thuật: `["tuyển", "hiring", "jd", "dev", "unity", "game", "c#", "c++", "java", "node", "backend", "fullstack", "intern", "fresher", "junior"]`.
4. **Kiểm tra trùng lặp nội dung & Ghost Job (`content_hash`):**
   - Chuẩn hóa `raw_text` (chữ thường, bỏ ký tự đặc biệt, bỏ khoảng trắng thừa, bỏ số điện thoại) rồi băm MD5/SimHash.
   - Nếu `content_hash` đã xuất hiện trong SQLite: Tăng `repost_count = repost_count + 1`, cập nhật `last_seen_at` rồi bỏ qua (không tốn quota gọi AI).
   - Nếu `repost_count >= 4` và khoảng cách `last_seen_at - first_seen_at > 30 ngày` -> Đánh dấu là **Ghost Job**.

### 5.4. Thang điểm AI & Cấu trúc Đầu ra (`ai_scorer.py`)
Sử dụng `gemini-2.5-flash` với cấu hình `response_mime_type="application/json"` theo thang điểm 100:

* **Tiêu chí 1 — Độ minh bạch (Tối đa 35 điểm):**
  * Có tên công ty/studio hoặc sản phẩm rõ ràng: **+15đ** (Giấu tên công ty: **0đ**).
  * Có khung lương cụ thể: **+10đ** (Lương thỏa thuận: **0đ**).
  * Có địa điểm làm việc và hình thức làm việc rõ ràng: **+10đ**.
* **Tiêu chí 2 — Độ uy tín của người đăng (Tối đa 25 điểm):**
  * Tech Lead / PM / Dev trong team đăng tuyển trực tiếp hoặc HR có email tên miền công ty (`@company.com`): **+25đ**.
  * Headhunter / Agency tuyển hộ hoặc chỉ nhận tin nhắn qua Zalo/Inbox cá nhân: **+5đ**.
* **Tiêu chí 3 — Độ khớp hồ sơ cá nhân (Tối đa 40 điểm):**
  * Khớp công nghệ mục tiêu (C#, Unity, Game Dev, C++, Java, Node.js, SQL): **+25đ**.
  * Đúng cấp bậc (Intern / Fresher / Junior dưới 2 năm kinh nghiệm): **+15đ** (Yêu cầu Senior trên 3-4 năm: **-30đ**).

**Cấu trúc JSON trả về từ Gemini:**
```json
{
  "is_valid_job": true,
  "company_name": "Tên công ty hoặc 'Ẩn danh'",
  "role_title": "Unity Game Developer",
  "seniority_level": "Fresher / Junior",
  "tech_stack": ["Unity", "C#", "3D"],
  "salary_info": "12 - 18 triệu VNĐ",
  "work_location": "Cầu Giấy, Hà Nội",
  "contact_method": "Gửi CV qua email hr@studio.vn",
  "score_breakdown": {
    "transparency_score": 30,
    "poster_credibility_score": 25,
    "profile_match_score": 35
  },
  "total_score": 90,
  "one_line_summary": "Studio tại Cầu Giấy tuyển trực tiếp Unity Dev (Fresher/Junior), lương 12-18M, có email công ty."
}
```

### 5.5. Quy tắc Phân luồng Đầu ra (`telegram_sheet.py`)
* `total_score < 50`: Lưu SQLite (`status = 'low_score'`), không thông báo.
* `50 <= total_score <= 69`: Lưu SQLite (`status = 'saved_backup'`), ghi vào tab **Dự Phòng** trên Google Sheets.
* `total_score >= 70`: Lưu SQLite (`status = 'notified'`), đẩy tin nhắn khẩn về **Telegram Bot** và ghi vào tab **Cần Nộp Ngay** trên Google Sheets.

---

## 6. Nguyên tắc An toàn Tài khoản (Anti-Ban Checklist)

- [x] **Không dùng tài khoản Facebook chính:** Sử dụng 1 tài khoản phụ đã tham gia sẵn các Group tuyển dụng IT/Game Dev.
- [x] **Không tự động đăng nhập lại mỗi lần chạy:** Luôn giữ nguyên phiên đăng nhập trong thư mục `chrome_profile/`.
- [x] **Giãn cách thời gian tự nhiên (Human Jitter):** Khoảng nghỉ giữa mỗi lần cuộn chuột lấy ngẫu nhiên từ `3.5` đến `8.5` giây; nghỉ giữa 2 Group từ `15` đến `30` giây.
- [x] **Giới hạn tần suất chạy:** Chỉ chạy **2–3 đợt/ngày** (ví dụ: 09:30, 14:30, 20:00), mỗi lần chỉ cuộn lấy 15–25 bài mới nhất mỗi Group.

---

## 7. Lộ trình Triển khai 4 Giai đoạn (Roadmap)

### Phase 1: Khung nền tảng, SQLite & LinkedIn Guest API (Buổi 1)
- [ ] Khởi tạo cấu trúc thư mục và cài đặt thư viện (`playwright`, `curl_cffi`, `beautifulsoup4`, `google-genai`).
- [ ] Viết `src/db.py` tạo bảng `jobs` và các hàm kiểm tra trùng lặp `raw_id`, `content_hash`.
- [ ] Viết `src/pipeline/pre_filter.py` xử lý lọc từ khóa và tạo mã băm nội dung.
- [ ] Viết `src/collectors/linkedin_api.py` kéo việc làm mới trong 24h qua và lưu thử vào SQLite.

### Phase 2: Tích hợp Bộ não Chấm điểm Gemini & Telegram Bot (Buổi 2)
- [ ] Tạo bot qua `@BotFather` trên Telegram, lấy `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`.
- [ ] Viết `src/pipeline/ai_scorer.py` tích hợp `gemini-2.5-flash` với Structured Outputs JSON Schema.
- [ ] Viết `src/notifiers/telegram_sheet.py` định dạng tin nhắn Markdown gửi về Telegram.
- [ ] Chạy thử luồng hoàn chỉnh: `LinkedIn API -> Pre-Filter -> Gemini Scorer -> SQLite -> Telegram`.

### Phase 3: Bắt gói tin Facebook Group qua Chrome CDP (Buổi 3)
- [ ] Tạo file `start_chrome_debug.bat`, mở Chrome đăng nhập sẵn tài khoản Facebook phụ.
- [ ] Viết `src/collectors/fb_cdp_listener.py` kết nối vào `localhost:9222`.
- [ ] Viết hàm bóc tách JSON từ các gói tin `/api/graphql/` để lấy `post_id`, nội dung đầy đủ và link bài viết.
- [ ] Đấu nối đầu ra của Facebook Collector vào chung phễu xử lý ở `main.py`.

### Phase 4: Đồng bộ Google Sheets & Lập lịch Tự động (Buổi 4)
- [ ] Tạo Google Sheets quản lý việc làm và gắn đoạn mã Google Apps Script (`doPost`) làm Webhook.
- [ ] Bổ sung hàm bắn dữ liệu lên Google Sheets Webhook trong `telegram_sheet.py`.
- [ ] Cài đặt Windows Task Scheduler tự động chạy bot vào 3 khung giờ cố định mỗi ngày.
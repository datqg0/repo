# src/pipeline/ai_scorer.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from src.config import GEMINI_API_KEY
except ImportError:
    from config import GEMINI_API_KEY

class JobEvaluation(BaseModel):
    """Cấu trúc dữ liệu thẩm định và chấm điểm chất lượng tin tuyển dụng."""
    is_valid_job: bool = Field(description="True nếu đây là tin tuyển dụng thật, False nếu là ứng viên tìm việc, khóa học bán lẻ hoặc tin rác")
    company_name: str = Field(description="Tên công ty/studio hoặc 'Ẩn danh'")
    role_title: str = Field(description="Tên vị trí công việc chính (vd: Unity Developer, Backend C#)")
    seniority_level: str = Field(description="Cấp bậc: Intern / Fresher / Junior / Middle / Senior")
    tech_stack: List[str] = Field(description="Danh sách các công nghệ/ngôn ngữ yêu cầu (vd: ['Unity', 'C#', 'SQL'])")
    salary_info: str = Field(description="Mức lương chi tiết (vd: '12 - 18 triệu', 'Thỏa thuận')")
    work_location: str = Field(description="Địa điểm làm việc cụ thể hoặc Remote / Hybrid")
    contact_method: str = Field(description="Phương thức nộp CV / Email / Link nộp")
    transparency_score: int = Field(description="Điểm minh bạch từ 0 đến 35 (có tên cty +15, lương rõ +10, địa chỉ rõ +10)")
    credibility_score: int = Field(description="Điểm uy tín người đăng từ 0 đến 25 (Tech lead/email domain cty +25, qua trung gian/inbox kín +5)")
    profile_match_score: int = Field(description="Điểm khớp kỹ năng từ 0 đến 40 (Khớp Game Unity/C#/C++ hoặc Backend Java/Node/SQL, trình độ Fresher/Junior)")
    total_score: int = Field(description="Tổng điểm chất lượng từ 0 đến 100")
    one_line_summary: str = Field(description="Tóm tắt 1 câu ngắn gọn lý do nên hay không nên nộp bài này")

SYSTEM_PROMPT = """
Bạn là chuyên gia thẩm định và chấm điểm tin tuyển dụng ngành CNTT. Hãy phân tích bài viết và chấm điểm khắt khe trên thang 100 dựa trên hồ sơ mục tiêu sau:
- Thế mạnh kỹ thuật: Lập trình Game (Unity 2D/3D, C#, C++, SDL, Phaser) và Phát triển phần mềm/Backend (Java Spring Boot, Node.js, C#, SQL).
- Cấp bậc mục tiêu: Thực tập sinh (Intern), Mới ra trường (Fresher), hoặc Junior (dưới 2 năm kinh nghiệm).
- Khu vực ưu tiên: Hà Nội hoặc Remote / Làm việc từ xa.

Quy tắc chấm điểm:
1. Độ minh bạch (Tối đa 35 điểm): Có tên công ty/studio (+15đ), có mức lương rõ ràng không phải thỏa thuận (+10đ), có địa chỉ làm việc cụ thể (+10đ).
2. Độ uy tín người đăng (Tối đa 25 điểm): Tech Lead, PM, Developer đăng tuyển trực tiếp hoặc email có tên miền công ty (+25đ). Chỉ nhận inbox/Zalo/cò mồi (+5đ).
3. Độ khớp hồ sơ cá nhân (Tối đa 40 điểm):
   - Đúng công nghệ (Unity, C#, C++, Java, Node.js, SQL): +25đ.
   - Đúng cấp bậc (Intern, Fresher, Junior): +15đ.
   - Nếu bài yêu cầu Senior (trên 3-4 năm kinh nghiệm) hoặc lệch hẳn sang Marketing, Sales, Designer: trừ -30 điểm profile_match_score.
"""

def evaluate_job_with_ai(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Gọi Gemini API (gemini-2.5-flash) với JSON Structured Output để trích xuất và chấm điểm tin tuyển dụng.
    """
    if not GEMINI_API_KEY or "DIEN_GEMINI" in GEMINI_API_KEY:
        print("[AI Scorer] ⚠️ Chưa cấu hình GEMINI_API_KEY trong file .env! Bỏ qua chấm điểm AI.")
        return None

    if genai is None:
        print("[AI Scorer] ⚠️ Thư viện google-genai chưa được cài đặt!")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Thử gọi gemini-2.5-flash, nếu không khả dụng thì fallback sang gemini-1.5-flash
        model_name = "gemini-2.5-flash"
        
        response = client.models.generate_content(
            model=model_name,
            contents=f"Phân tích bài đăng tuyển dụng sau và trả về theo JSON Schema:\n\n{raw_text[:4000]}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=JobEvaluation,
                temperature=0.1,
            ),
        )
        
        if hasattr(response, "parsed") and response.parsed:
            data = response.parsed.model_dump()
            # Đảm bảo tổng điểm khớp
            calculated_total = (
                data.get("transparency_score", 0) +
                data.get("credibility_score", 0) +
                data.get("profile_match_score", 0)
            )
            # Giới hạn trong khoảng 0 - 100
            data["total_score"] = max(0, min(100, calculated_total))
            return data
            
        return None
    except Exception as e:
        print(f"[AI Scorer] Lỗi khi gọi Gemini API ({e})")
        return None

if __name__ == "__main__":
    sample_text = """
    [Hà Nội] Cần tuyển gấp 02 Unity Developer (Fresher / Junior)
    Công ty: Studio Game Vina, địa chỉ: Duy Tân, Cầu Giấy, Hà Nội.
    Mức lương: 12 - 18 triệu VNĐ.
    Yêu cầu: Nắm chắc C#, có sản phẩm Unity demo.
    Liên hệ gửi CV về: hr@vinagame-studio.vn hoặc inbox.
    """
    res = evaluate_job_with_ai(sample_text)
    print("Kết quả chấm điểm AI:", res)

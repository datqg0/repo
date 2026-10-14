/**
 * Google Apps Script - JobHunter Bot Webhook
 * 
 * HƯỚNG DẪN CÀI ĐẶT:
 * 1. Mở trang Google Sheets mới (https://sheets.new)
 * 2. Vào menu: Tiện ích mở rộng (Extensions) -> Apps Script
 * 3. Xóa hết code cũ, dán toàn bộ đoạn code này vào
 * 4. Bấm "Triển khai" (Deploy) -> "Tùy chọn triển khai mới" (New deployment)
 * 5. Chọn loại: "Ứng dụng web" (Web app)
 *    - Mô tả: JobHunter Webhook
 *    - Thực thi dưới dạng: Tôi (tài khoản của bạn)
 *    - Ai có quyền truy cập: Bất kỳ ai (Anyone)
 * 6. Bấm Triển khai, cấp quyền nếu được hỏi và copy "URL ứng dụng web"
 * 7. Dán URL vừa copy vào biến GOOGLE_SHEET_WEBHOOK trong file .env
 */

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var tabName = data.tab || "Cần Nộp Ngay";
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(tabName);
    
    // Nếu sheet chưa tồn tại thì tạo mới và khởi tạo tiêu đề
    if (!sheet) {
      sheet = ss.insertSheet(tabName);
      var headers = [
        "Thời Gian", 
        "Điểm AI", 
        "Vị Trí Tuyển Dụng", 
        "Công Ty", 
        "Cấp Bậc", 
        "Mức Lương", 
        "Địa Điểm", 
        "Công Nghệ (Tech Stack)", 
        "Tóm Tắt AI", 
        "Đường Dẫn Bài Đăng", 
        "Mã ID Gốc",
        "Nguồn"
      ];
      sheet.appendRow(headers);
      var headerRange = sheet.getRange(1, 1, 1, headers.length);
      headerRange.setFontWeight("bold");
      headerRange.setBackground(tabName === "Cần Nộp Ngay" ? "#d4edda" : "#fff3cd");
      sheet.setFrozenRows(1);
    }
    
    // Thêm dòng dữ liệu mới
    var timestamp = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM-dd HH:mm:ss");
    var rowData = [
      timestamp,
      data.score || 0,
      data.role_title || "",
      data.company || "Ẩn danh",
      data.seniority || "",
      data.salary || "Thỏa thuận",
      data.location || "",
      data.tech_stack || "",
      data.summary || "",
      data.url || "",
      data.raw_id || "",
      data.source || ""
    ];
    
    sheet.appendRow(rowData);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success", 
      message: "Đã lưu thành công vào tab " + tabName
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error", 
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

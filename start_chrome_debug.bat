@echo off
chcp 65001 >nul
echo ======================================================================
echo   JOBHUNTER BOT - KHỞI ĐỘNG CHROME CHẾ ĐỘ DEBUGGING (PORT 9222)
echo ======================================================================
echo.

set PROFILE_DIR=%~dp0chrome_profile
if not exist "%PROFILE_DIR%" (
    echo [*] Đang tạo thư mục lưu hồ sơ Chrome: "%PROFILE_DIR%"
    mkdir "%PROFILE_DIR%"
)

set CHROME_PATH=""
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME_PATH%=="" (
    echo [LỖI] Không tìm thấy file chrome.exe trên máy của bạn!
    echo Vui lòng cài đặt Google Chrome hoặc chỉnh lại đường dẫn trong file này.
    pause
    exit /b 1
)

echo [*] Đang khởi chạy Chrome với cổng 9222...
echo [*] Thư mục profile: "%PROFILE_DIR%"
echo.
echo [HƯỚNG DẪN]
echo 1. Một cửa sổ Chrome mới sẽ hiện ra.
echo 2. Hãy đăng nhập tài khoản Facebook (nick phụ) của bạn vào cửa sổ đó.
echo 3. Giữ cửa sổ Chrome này mở (có thể thu nhỏ) khi chạy JobHunter Bot.
echo.

%CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check

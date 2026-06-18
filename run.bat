@echo off
REM ============================================================
REM  HungArch AI Render - chay 1 cham tren Windows
REM  - Tao virtualenv (lan dau)
REM  - Cai thu vien
REM  - Khoi dong server va mo trinh duyet
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\" (
  echo [1/3] Tao moi truong ao Python...
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo [2/3] Cai/ cap nhat thu vien...
python -m pip install --upgrade pip >nul
python -m pip install -r backend\requirements.txt

if not exist ".env" (
  echo.
  echo [!] Chua co file .env - dang tao tu mau .env.example
  copy ".env.example" ".env" >nul
  echo [!] Hay mo file .env va dien GEMINI_API_KEY truoc khi render.
  echo.
)

REM Giai phong cong 8000 neu con tien trinh cu dang giu (tranh loi "address already in use")
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [3/3] Khoi dong server tai http://localhost:8000 ...
start "" http://localhost:8000
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000

endlocal

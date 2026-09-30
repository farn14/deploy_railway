@echo off
chcp 65001 >nul
echo ===================================================
echo  🚀 Safe Gateway ^& Live AI Engine (Local Test)
echo ===================================================
echo กำลังเริ่มต้นเซิร์ฟเวอร์...
start http://localhost:8080
python app.py
pause

@echo off
chcp 65001 > nul
echo ===============================================================
echo   SAITEK Tektronix Quick Start SW Launcher
echo   8 Manual Categories Integrated Control ^& Measurement Suite
echo ===============================================================
cd /d "%~dp0"
python "02.src\06.Main\main_app.py"
if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 문제가 발생했습니다.
    pause
)

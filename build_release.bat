@echo off
chcp 65001 >nul
echo ============================================================================
echo   SAITEK Tektronix Quick Start SW - 배포용 설치파일/실행파일 자동 빌드
echo ============================================================================
echo.
"C:\Users\jwlee1\AppData\Local\Programs\Python\Python314\python.exe" "%~dp004.tools\01.Scripts\build_release.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 빌드 중 오류가 발생했습니다.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [OK] 빌드가 완료되었습니다. 06.Release 폴더를 확인하세요.
pause

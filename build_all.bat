@echo off
chcp 65001 >nul
setlocal

:: bat 파일이 있는 폴더로 이동
cd /d "%~dp0"

set VERSION=8.0
set APP_NAME=NetworkAutomation

echo =====================================================
echo   Network Automation v%VERSION% 빌드 스크립트
echo   설치 버전(Setup.exe) + 포터블(ZIP) 생성
echo =====================================================
echo.

:: ── 이전 빌드 정리 ───────────────────────────────────────────────
echo [1/4] 이전 빌드 정리...
if exist "dist"   rmdir /S /Q "dist"
if exist "build"  rmdir /S /Q "build"
if exist "output" rmdir /S /Q "output"
mkdir output
echo 완료
echo.

:: ── PyInstaller 빌드 ─────────────────────────────────────────────
echo [2/4] PyInstaller 빌드 중... (시간이 걸립니다)
echo y | python -m PyInstaller --clean NetworkAutomation.spec
if errorlevel 1 (
    echo.
    echo [오류] PyInstaller 빌드 실패!
    pause
    exit /b 1
)
echo 완료
echo.

:: ── Inno Setup 설치 버전 생성 ────────────────────────────────────
echo [3/4] 설치 버전(Setup.exe) 생성 중...

:: Inno Setup 경로 자동 탐색
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if %ISCC%=="" (
    echo [오류] Inno Setup 6 이 설치되어 있지 않습니다.
    echo   https://jrsoftware.org/isdl.php 에서 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

%ISCC% installer.iss
if errorlevel 1 (
    echo [오류] Inno Setup 빌드 실패!
    pause
    exit /b 1
)
echo 완료
echo.

:: ── 포터블 ZIP 생성 ───────────────────────────────────────────────
echo [4/4] 포터블 ZIP 생성 중...
set ZIP_NAME=%APP_NAME%_Portable_v%VERSION%.zip
if exist "output\%ZIP_NAME%" del /Q "output\%ZIP_NAME%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\%APP_NAME%\*' -DestinationPath 'output\%ZIP_NAME%'"
if errorlevel 1 (
    echo [오류] ZIP 생성 실패!
    pause
    exit /b 1
)
echo 완료
echo.

:: ── 결과 확인 ────────────────────────────────────────────────────
echo =====================================================
echo   빌드 완료!
echo =====================================================
echo.
if exist "output\%APP_NAME%_Setup_v%VERSION%.exe" (
    echo  [설치본]   output\%APP_NAME%_Setup_v%VERSION%.exe
)
if exist "output\%ZIP_NAME%" (
    echo  [포터블]   output\%ZIP_NAME%
)
echo.
echo output\ 폴더를 확인하세요.
echo =====================================================
echo.
pause

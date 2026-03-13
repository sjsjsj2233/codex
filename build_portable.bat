@echo off
chcp 65001 >nul
echo ========================================
echo    네트워크 자동화 프로그램 v7.0
echo    포터블 버전 빌드 스크립트
echo ========================================
echo.

echo [1/4] 이전 빌드 폴더 정리...
if exist "dist" rmdir /S /Q "dist"
if exist "build" rmdir /S /Q "build"
echo 완료!
echo.

echo [2/4] PyInstaller로 빌드 중...
python -m PyInstaller --clean NetworkAutomation.spec
if errorlevel 1 (
    echo.
    echo 오류: 빌드 실패!
    pause
    exit /b 1
)
echo 완료!
echo.

echo [3/4] 포터블 ZIP 패키지 생성 중...
powershell -command "Compress-Archive -Path 'dist\NetworkAutomation\*' -DestinationPath 'NetworkAutomation_v7.0_Portable.zip' -Force"
echo 완료!
echo.

echo [4/4] 빌드 결과 확인...
if exist "NetworkAutomation_v7.0_Portable.zip" (
    echo.
    echo ========================================
    echo 빌드 성공!
    echo 파일: NetworkAutomation_v7.0_Portable.zip
    echo 크기: 약 105MB
    echo ========================================
) else (
    echo.
    echo 오류: ZIP 파일 생성 실패!
)

echo.
pause

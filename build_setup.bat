@echo off
chcp 65001 >nul
echo ========================================
echo    $∏Ãl êŸT \¯® v7.0
echo    Setup x§®Ï L‹ §lΩ∏
echo ========================================
echo.

echo [1/5] t L‹ ÙT ¨...
if exist "dist" rmdir /S /Q "dist"
if exist "build" rmdir /S /Q "build"
echo DÃ!
echo.

echo [2/5] PyInstaller\ L‹ ...
pyinstaller --clean NetworkAutomation.spec
if errorlevel 1 (
    echo.
    echo $X: L‹ ‰(!
    pause
    exit /b 1
)
echo DÃ!
echo.

echo [3/5] Inno Setup Ux...
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_PATH% (
    echo $X: Inno Setupt $X¿ JXµ»‰!
    echo Inno Setup 6D ‰¥\‹XÏ $Xt¸8î.
    echo ‰¥\‹: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
echo DÃ!
echo.

echo [4/5] Setup x§®Ï ›1 ...
%INNO_PATH% "setup_installer.iss"
if errorlevel 1 (
    echo.
    echo $X: Setup ›1 ‰(!
    pause
    exit /b 1
)
echo DÃ!
echo.

echo [5/5] L‹ ∞¸ Ux...
if exist "NetworkAutomation_v7.0_Setup.exe" (
    echo.
    echo ========================================
    echo L‹ 1ı!
    echo |: NetworkAutomation_v7.0_Setup.exe
    echo ========================================
) else (
    echo.
    echo $X: Setup |t ›1¿ JXµ»‰!
)

echo.
pause


@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting Cargo dependency visualizer...
echo.

if "%~1"=="" (
    py -3 src\main.py --test --repository examples\repository.json --package A --version test --ascii --stage 5
) else (
    py -3 src\main.py %*
)

echo.
echo Exit code: %errorlevel%
echo.
pause

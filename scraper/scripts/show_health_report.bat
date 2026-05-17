@echo off
setlocal
cd /d "%~dp0.."
python "%~dp0show_health_report.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%

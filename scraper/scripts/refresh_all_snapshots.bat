@echo off
rem Backward-compatible alias kept for older notes/workflows.
rem The clearer name is refresh_non_weapon_uniques.bat.
echo [deprecated] refresh_all_snapshots.bat is now an alias for refresh_non_weapon_uniques.bat.
echo [deprecated] Use scraper\scripts\refresh_non_weapon_uniques.bat going forward.
call "%~dp0refresh_non_weapon_uniques.bat"
exit /b %ERRORLEVEL%

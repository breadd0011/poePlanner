@echo off
rem Regenerate planner payload from local snapshots/cache.
call "%~dp0_run_poc.bat" --debug --write-schema --copy-web
exit /b %ERRORLEVEL%

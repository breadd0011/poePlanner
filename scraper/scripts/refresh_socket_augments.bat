@echo off
rem Force-refresh all socket-compatible augment data, rebuild the planner payload, and print coverage warnings.
rem Use after augment parser changes or when socket augment coverage/tooltip data looks stale.
call "%~dp0_run_poc.bat" --force-refresh --debug --write-schema
exit /b %ERRORLEVEL%

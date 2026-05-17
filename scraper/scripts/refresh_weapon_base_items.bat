@echo off
rem Refresh weapon base item catalogue pages only. Skips unique detail hydration.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Weapons --write-schema
exit /b %ERRORLEVEL%

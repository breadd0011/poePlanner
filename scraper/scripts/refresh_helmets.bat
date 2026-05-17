@echo off
rem Refresh Helmet class page + unique detail snapshots, then regenerate payload.
call "%~dp0_run_poc.bat" --update-snapshots --categories Helmets --debug --write-schema
exit /b %ERRORLEVEL%

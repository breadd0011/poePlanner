@echo off
rem Refresh accessory modifier snapshots: Rings, Amulets, Belts.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Rings,Amulets,Belts --debug --write-schema
exit /b %ERRORLEVEL%

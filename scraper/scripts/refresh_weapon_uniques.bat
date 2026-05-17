@echo off
rem Refresh production weapon/Talisman unique class pages and unique detail snapshots.
rem This can take a while because the Weapons alias expands to many PoE2DB weapon classes. Traps are out of scope.
call "%~dp0_run_poc.bat" --update-snapshots --categories Weapons --debug --write-schema
exit /b %ERRORLEVEL%

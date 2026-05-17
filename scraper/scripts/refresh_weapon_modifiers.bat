@echo off
rem Refresh weapon modifier snapshots. Skips unique detail hydration.
rem The Weapons alias expands to each concrete PoE2DB weapon class and writes class-page ModifiersCalc HTML.
rem Supported weapon classes, including Talismans, are production-required. Traps are intentionally out of scope.
echo [info] Refreshing weapon modifier snapshots. This fetches weapon class pages only.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Weapons --debug --write-schema
exit /b %ERRORLEVEL%

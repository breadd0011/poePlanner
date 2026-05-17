@echo off
rem Refresh Life Flask, Mana Flask, and Charm class pages, modifiers, base items, and unique detail snapshots.
call "%~dp0_run_poc.bat" --update-snapshots --categories "Life Flasks","Mana Flasks",Charms --debug --write-schema
exit /b %ERRORLEVEL%

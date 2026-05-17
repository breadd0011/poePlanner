@echo off
rem Refresh offhand modifier snapshots: Shields, Foci, Quivers.
rem Shields use subtype modifier pages; Foci and Quivers use class-level modifier pages.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Shields,Foci,Quivers --debug --write-schema
exit /b %ERRORLEVEL%

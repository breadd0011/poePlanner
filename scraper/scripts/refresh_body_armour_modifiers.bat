@echo off
rem Refresh Body Armour subtype modifier snapshots.
rem Body Armours use six defence-profile pages: str, dex, int, str_dex, str_int, dex_int.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories "Body Armours" --debug --write-schema
exit /b %ERRORLEVEL%

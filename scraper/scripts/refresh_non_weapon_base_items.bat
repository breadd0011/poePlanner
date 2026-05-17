@echo off
rem Refresh non-weapon base item catalogue pages only. Skips unique detail hydration.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Gloves,Boots,Helmets,"Body Armours",Shields,Foci,Quivers,Rings,Amulets,Belts,"Life Flasks","Mana Flasks",Charms --write-schema
exit /b %ERRORLEVEL%

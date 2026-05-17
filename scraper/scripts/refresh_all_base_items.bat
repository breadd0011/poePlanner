@echo off
rem Refresh all supported base item catalogue pages. Skips unique detail hydration.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Gloves,Boots,Helmets,"Body Armours",Shields,Foci,Quivers,Rings,Amulets,Belts,"Life Flasks","Mana Flasks",Charms,Weapons --write-schema
exit /b %ERRORLEVEL%

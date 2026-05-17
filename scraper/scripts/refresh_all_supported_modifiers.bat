@echo off
rem Refresh every modifier class currently marked required by the health report.
rem Covers armour, body armour, accessories, offhands, utility slots, and supported weapon classes. Skips unique detail hydration.
rem Weapons expands to supported weapon classes including Talismans. Traps are intentionally out of scope.
call "%~dp0_run_poc.bat" --update-snapshots --skip-unique-details --categories Gloves,Boots,Helmets,"Body Armours",Rings,Amulets,Belts,Shields,Foci,Quivers,"Life Flasks","Mana Flasks",Charms,Weapons --debug --write-schema
exit /b %ERRORLEVEL%

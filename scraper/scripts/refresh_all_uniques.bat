@echo off
rem Full unique refresh: non-weapon, flask/charm, and weapon unique classes.
rem This is the heavy crawl. Prefer refresh_non_weapon_uniques.bat unless you need weapon uniques too.
echo [info] Full unique refresh selected. This may take several minutes.
call "%~dp0_run_poc.bat" --update-snapshots --categories Gloves,Boots,Helmets,"Body Armours",Shields,Foci,Quivers,Rings,Amulets,Belts,"Life Flasks","Mana Flasks",Charms,Weapons --debug --write-schema
exit /b %ERRORLEVEL%

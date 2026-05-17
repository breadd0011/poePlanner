@echo off
rem Refresh non-weapon plus flask/charm unique class pages and unique detail snapshots.
rem Use this for normal unique/flavourText refreshes.
call "%~dp0_run_poc.bat" --update-snapshots --categories Gloves,Boots,Helmets,"Body Armours",Shields,Foci,Quivers,Rings,Amulets,Belts,"Life Flasks","Mana Flasks",Charms --debug --write-schema
exit /b %ERRORLEVEL%

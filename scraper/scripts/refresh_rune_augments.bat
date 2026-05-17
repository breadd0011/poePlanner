@echo off
rem Backward-compatible alias. Socket augment data now includes runes plus other game-supported socketable augments.
call "%~dp0refresh_socket_augments.bat"
exit /b %ERRORLEVEL%

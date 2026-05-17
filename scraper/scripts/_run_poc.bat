@echo off
setlocal

rem Shared runner for run_poc.py.
rem Keeps all public helper scripts Windows-CMD friendly and runnable from any folder.

pushd "%~dp0.."
set "PYTHONPATH=."
python "run_poc.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

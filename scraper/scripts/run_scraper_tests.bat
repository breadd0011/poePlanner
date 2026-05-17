@echo off
setlocal

rem Run the focused scraper/payload regression suite.
rem Works whether you run it from the project root or from the scripts folder.

pushd "%~dp0.."
set "PYTHONPATH=."
python -m pytest -p no:cacheprovider ^
  tests/test_payload_contract.py ^
  tests/test_unique_flavour_text.py ^
  tests/test_unique_boot_flavour_text.py ^
  tests/test_unique_detail_flavour_hydration.py ^
  tests/test_health_report.py ^
  tests/test_non_armour_modifier_pipeline.py
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

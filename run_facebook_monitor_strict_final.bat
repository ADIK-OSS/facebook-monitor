@echo off
cd /d %~dp0
echo Running facebook_monitor_strict_final.py ...
python facebook_monitor_strict_final.py
echo.
echo Press any key to exit...
pause >nul
@echo off
rem GxP Quality Command Centre - start on Windows with Python 3.14 (falls back to the default python).
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.14 run.py %*
) else (
  python run.py %*
)

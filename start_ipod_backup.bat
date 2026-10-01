@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo Python 3.10 or newer is required. Install it from https://www.python.org/downloads/
    set "RESULT=1"
    goto finish
)
if not exist ".venv\Scripts\python.exe" (
    echo Creating this tool's private Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create the Python environment.
        set "RESULT=1"
        goto finish
    )
)
".venv\Scripts\python.exe" -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo The existing .venv uses Python older than 3.10. Remove .venv and retry.
    set "RESULT=1"
    goto finish
)
echo Checking required packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo Could not install packages listed in requirements.txt.
    set "RESULT=1"
    goto finish
)
".venv\Scripts\python.exe" start_backup.py
set "RESULT=%ERRORLEVEL%"
:finish
echo.
if not "%RESULT%"=="0" echo Backup did not finish successfully. Read the message above.
pause
exit /b %RESULT%

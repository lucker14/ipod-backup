@echo off
cd /d "%~dp0"
py -3 start_backup.py
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Backup did not finish successfully. Read the message above.
pause
exit /b %RESULT%
